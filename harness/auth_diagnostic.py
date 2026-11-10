"""Classify saved token errors locally; never export raw authentication text."""

import argparse
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile

from .asar import HarnessError
from . import game_launch, reward_probe

MAX_LOG_BYTES = 2 * 1024 * 1024
MAX_ERROR_CHARS = 32768
TOKEN_ERROR = "OAuth authorization code grant failed:"
OAUTH_ERRORS = frozenset({
    "invalid_request", "invalid_client", "invalid_grant", "unauthorized_client",
    "unsupported_grant_type", "invalid_scope", "access_denied", "server_error",
    "temporarily_unavailable",
})


def classify(texts):
    """Return only fixed vocabulary/booleans, even for secret-bearing input."""
    bodies = []
    complete = False
    callback_failure = False
    for text in texts:
        complete |= "[AuthorizationWorkflow] Completed token exchange" in text
        callback_failure |= "[AuthorizationWorkflow] Failed to exchange token or complete authorization:" in text
        # Bound both the number and length of inspected errors. Unrelated HTML
        # elsewhere in the app log must not be mistaken for a token response.
        for match in list(re.finditer(re.escape(TOKEN_ERROR), text))[-8:]:
            body = text[match.end():match.end() + MAX_ERROR_CHARS]
            body = re.split(r"\n\[\d{4}-\d\d-\d\d", body, maxsplit=1)[0]
            bodies.append(body)
    html = any(re.search(r"<!doctype\s+html|<html(?:\s|>)", b, re.I) for b in bodies)
    challenge = any(any(marker in b.lower() for marker in (
        "cf-chl-", "/cdn-cgi/challenge-platform/", "enable javascript and cookies", "just a moment",
    )) for b in bodies)
    cloudflare = any("cloudflare" in b.lower() for b in bodies)
    codes = set()
    for body in bodies:
        try:
            value, _ = json.JSONDecoder().raw_decode(body.lstrip())
        except (ValueError, RecursionError):
            continue
        if isinstance(value, dict) and isinstance(value.get("error"), str) and value["error"] in OAUTH_ERRORS:
            codes.add(value["error"])
    category = ("UPSTREAM_SECURITY_PAGE" if challenge else "OAUTH_PROTOCOL_ERROR" if codes
                else "UPSTREAM_HTML_ERROR" if html else "UNCLASSIFIED_TOKEN_ERROR" if bodies
                else "NO_TOKEN_ERROR_BODY")
    return {"classification": category, "token_error_logged": bool(bodies),
            "token_exchange_completed_logged": complete, "callback_failure_logged": callback_failure,
            "html_marker": html, "browser_challenge_marker": challenge,
            "cloudflare_marker": cloudflare, "oauth_error_codes": sorted(codes)}


def _private_directory(path):
    if path.resolve(strict=True) != path:
        raise HarnessError("Redirected diagnostic directory")
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise HarnessError("Diagnostic directory must be private and owned")


def _read_owned(path, maximum, *, tail=False):
    # Parent directories are checked separately. Refuse links and special files
    # before and after opening so even a failed probe cannot read a redirected log.
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid() or before.st_nlink != 1:
        raise HarnessError("Unsafe diagnostic file")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1
                or (info.st_dev, info.st_ino) != (before.st_dev, before.st_ino)):
            raise HarnessError("Changed diagnostic file")
        truncated = info.st_size > maximum
        if truncated and not tail:
            raise HarnessError("Diagnostic metadata exceeds limit")
        if truncated:
            stream.seek(-maximum, os.SEEK_END)
        return stream.read(maximum).decode("utf-8", "replace"), truncated


def inspect_attempt(attempt, home):
    attempt = Path(attempt).absolute()
    session = reward_probe._private_session(attempt.parent, home)
    if not re.fullmatch(r"outer-attempt-[A-Za-z0-9_-]{8}", attempt.name):
        raise HarnessError("Not a controlled attempt")
    _private_directory(attempt)
    _private_directory(attempt / "profile")
    manifest = json.loads(_read_owned(attempt / "manifest.json", 32768)[0])
    launch = json.loads(_read_owned(attempt / "launch.json", 32768)[0])
    if (not isinstance(manifest, dict) or manifest.get("controlled_access_version") != 1
            or manifest.get("prepared_session") != str(session)
            or not isinstance(launch, dict) or launch.get("manual_oauth") is not True
            or launch.get("outer_sandbox_retained") is not True):
        raise HarnessError("Not a confined controlled OAuth attempt")
    texts = []
    limited = False
    for path in (attempt / "stdout.log", attempt / "profile/log.log"):
        try:
            text, truncated = _read_owned(path, MAX_LOG_BYTES, tail=True)
        except FileNotFoundError:
            continue
        texts.append(text)
        limited |= truncated
    return {"schema": 1, "mode": "SAVED_AUTH_ERROR_CLASSIFICATION", **classify(texts),
            "log_files_checked": len(texts), "log_tail_limit_reached": limited,
            "raw_logs_included": False, "account_details_included": False, "network_requests_made": False}


def run(attempt):
    _, home, _ = game_launch.test_identity("sts2test", game_launch.PROTECTED_HOME)
    safe = inspect_attempt(attempt, home)
    with tempfile.NamedTemporaryFile(prefix="sts2test-auth-error.", suffix=".json", dir="/private/tmp", delete=False) as output:
        output.write((json.dumps(safe, indent=2) + "\n").encode())
        os.fchmod(output.fileno(), 0o644)
    print("Diagnostic file: " + output.name)
    return safe


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("attempt", type=Path)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(run(args.attempt), indent=2))
        return 0
    except (HarnessError, OSError, ValueError, TypeError, RuntimeError):
        # Raw exceptions and paths could embed account/token material.
        print("Saved authentication diagnostic unavailable. Keep raw logs private.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
