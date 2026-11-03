"""Prepare and supervise manual OAuth/public-data experiments; no login automation."""
import argparse
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from . import cli, game_debug, game_launch, reward_probe
from .asar import HarnessError, sha256
from .gateway import COMPANION_USER_AGENT, Gateway

EVENTS = {"bootstrap", "ready", "window-detected", "attach-attempt", "reader-connected",
          "reward", "manual-sign-in-ready", "authenticated"}
ROUTES = {"oauth_token", "accounts_account", "sts2_exchange", "sts2_account", "sts2_features",
          "tier_resolve", "public_json", "commentary_events", "denied", "error", "unknown"}
ERROR_KINDS = {"TLS_CERTIFICATE_ERROR", "TLS_PROTOCOL_ERROR", "DNS_ERROR", "TIMEOUT",
               "INCOMPLETE_RESPONSE", "CONNECTION_REFUSED", "CONNECTION_CLOSED", "OS_ERROR",
               "RESPONSE_INTERFACE_ERROR", "INTERNAL_SHAPE_ERROR", "UNKNOWN_TRANSPORT_ERROR"}
ERROR_STAGES = {"LOCAL_REQUEST", "UPSTREAM_TRANSPORT", "UPSTREAM_RESPONSE", "LOCAL_RESPONSE", "UNKNOWN_STAGE"}


def proposal(session):
    session = Path(session).resolve(strict=True)
    manifest = cli.read_json(session / "manifest.json")
    if manifest.get("controlled_access_version") != 1:
        raise HarnessError("Prepare a current controlled-access companion first")
    for filename, key in (("gateway.py", "controlled_gateway_sha256"), ("controlled_network.cjs", "controlled_network_sha256")):
        if sha256(Path(__file__).with_name(filename).read_bytes()) != manifest.get(key):
            raise HarnessError("Controlled policy changed since preparation; prepare a new review")
    return {"scope": "MANUAL_OAUTH_AND_PUBLIC_DATA_ONLY", "session": str(session),
            "companion_remote_network": "DENIED_UNCHANGED_OUTER_POLICY",
            "oauth_scope": "companion:full-access", "browser_network": "OUTSIDE_COMPANION_GATEWAY",
            "outbound_user_agent": COMPANION_USER_AGENT,
            "preflight": "FIXED_DATA_ACCOUNT_GET_AND_TOKEN_POST", "preflight_maximum_requests": 2,
            "failure_export": "FIXED_CATEGORY_STAGE_TIMING_ONLY",
            "keytar_credentials": "SESSION_MEMORY_ONLY", "raw_logs": "PRIVATE_NEVER_SHARED",
            "auth_hosts": ["api.accounts.untapped.gg", "api.sts2.untapped.gg"],
            "public_hosts": ["sts2json.untapped.gg", "sts2.untapped.gg", "api.sts2.untapped.gg"],
            "allowed_purposes": ["oauth_code_or_refresh", "account", "sts2_token_exchange", "features",
                                 "six_public_game_json_files", "event_commentary", "creator_tier_resolve"],
            "blocked": ["stats_gameplay_context", "predictions", "run_history", "uploads", "upload_tokens",
                        "anonymous_claims", "telemetry", "updates", "artwork", "unreviewed_routes"],
            "callback_ports": [17791, 17799], "maximum_seconds": 300, "post_auth_maximum_seconds": 45,
            "gateway_sha256": sha256(Path(__file__).with_name("gateway.py").read_bytes()),
            "network_adapter_sha256": sha256(Path(__file__).with_name("controlled_network.cjs").read_bytes()),
            "proposal_only": True, "requires_explicit_approval": True}


def sanitized_events(events):
    result = []
    for event in events[:200]:
        if not isinstance(event, dict) or event.get("event") not in EVENTS:
            continue
        row = {"event": event["event"]}
        # Never copy arbitrary values or error strings from private logs/events.
        stamp = event.get("time", "")
        if isinstance(stamp, str) and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z", stamp):
            row["time"] = stamp
        if row["event"] == "reward":
            cards = cli.validate_cards(event.get("cards"))
            if any(not re.fullmatch(r"[A-Z0-9_]{1,80}", card["id"]) for card in cards):
                raise HarnessError("Unsupported reward identifier in controlled export")
            row["cards"] = [{key: card[key] for key in ("id", "upgradeLevel", "cx", "cy", "width", "height", "scaleX", "scaleY") if key in card} for card in cards]
        result.append(row)
    return result


def sanitized_report(report):
    result = {}
    for key in ("static_inspection", "startup", "companion_initialization", "window_detection",
                "attachment", "state_reading", "overlay", "reward_comparison"):
        value = report.get(key)
        if isinstance(value, str) and re.fullmatch(r"[A-Z0-9_]{1,80}", value):
            result[key] = value
    for key in ("terms_screen_logged", "settings_property_error", "public_data_cache_missing"):
        result[key] = report.get(key) is True
    result["startup_blocker_count"] = len(report.get("startup_blockers", []))
    result["launch"] = {key: value for key, value in (report.get("launch") or {}).items()
                        if key in {"seconds_limit", "chromium_sandbox", "outer_sandbox_retained",
                                   "fresh_profile", "time_limit_reached", "exit_code", "manual_oauth",
                                   "raw_logs_private", "post_auth_limit", "authenticated_event_observed", "app_started"}
                        and (value is None or type(value) in (int, bool))}
    return result


def sanitized_error(row):
    safe = {}
    if "transport_error" in row:
        kind = row["transport_error"]
        safe["transport_error"] = kind if isinstance(kind, str) and kind in ERROR_KINDS else "UNKNOWN_TRANSPORT_ERROR"
    for key in ("os_errno", "certificate_verify_code"):
        value = row.get(key)
        if type(value) is int and -65536 <= value <= 65536:
            safe[key] = value
    return safe


def sanitized_preflight(raw):
    raw = raw if isinstance(raw, dict) else {}
    source_rows = raw.get("results", [])
    source_rows = source_rows if isinstance(source_rows, list) else []
    rows = []
    for row in source_rows[:2]:
        row = row if isinstance(row, dict) else {}
        route = row.get("route")
        item = {"route": route if isinstance(route, str) and route in ROUTES else "unknown", **sanitized_error(row)}
        value = row.get("status")
        if type(value) is int and 100 <= value <= 599:
            item["status"] = value
        value = row.get("body_bytes")
        if type(value) is int and 0 <= value <= 32769:
            item["body_bytes"] = value
        if isinstance(row.get("response_kind"), str) and row["response_kind"] in {"JSON", "TEXT", "HTML", "OTHER"}:
            item["response_kind"] = row["response_kind"]
        item["json_object"] = row.get("json_object") is True
        rows.append(item)
    passed = (raw.get("passed") is True and type(raw.get("requests_attempted")) is int
              and raw["requests_attempted"] == 2 and len(source_rows) == 2
              and [row["route"] for row in rows] == ["accounts_account", "oauth_token"]
              and all(row.get("status") == 401 and row.get("response_kind") == "JSON" and row["json_object"]
                      and row.get("body_bytes", 32769) <= 32768 and "transport_error" not in row for row in rows))
    return {"passed": passed, "results": rows, "requests_attempted": len(rows),
            "maximum_requests": 2, "real_credentials_sent": False}


def sanitized_failures(rows, preflight_count):
    safe = []
    for index, row in enumerate(rows[:32]):
        row = row if isinstance(row, dict) else {}
        route, stage = row.get("route"), row.get("stage")
        item = {"route": route if isinstance(route, str) and route in ROUTES else "unknown",
                "stage": stage if isinstance(stage, str) and stage in ERROR_STAGES else "UNKNOWN_STAGE",
                "phase": "preflight" if index < preflight_count else "companion", **sanitized_error(row)}
        value = row.get("elapsed_ms")
        if type(value) is int and 0 <= value <= 300000:
            item["elapsed_ms"] = value
        safe.append(item)
    return safe


def safe_counts(counts):
    return [{"route": route, "status": status, "count": count}
            for (route, status), count in sorted(counts.items())
            if route in ROUTES and type(status) is int and 100 <= status <= 599
            and type(count) is int and 0 < count <= 1000000]


def not_started_report(reason, seconds):
    return {"static_inspection": "VERIFIED", "startup": reason, "companion_initialization": "NOT_OBSERVED",
            "window_detection": "UNTESTED", "attachment": "UNTESTED", "state_reading": "UNTESTED",
            "overlay": "UNTESTED_REQUIRES_VISUAL_CHECK", "reward_comparison": "UNTESTED_USE_COMPARE_REWARD",
            "launch": {"seconds_limit": seconds, "post_auth_limit": 45, "manual_oauth": True, "app_started": False}}


def run(session, *, approved=False, observe=False, seconds=300):
    if not approved:
        raise HarnessError("Explicit approval required for controlled OAuth/data access")
    if type(seconds) is not int or not 1 <= seconds <= 300:
        raise HarnessError("Controlled companion limit is 1–300 seconds")
    _, home, _ = game_launch.test_identity("sts2test", game_launch.PROTECTED_HOME)
    session = reward_probe._private_session(session, home)
    proposal(session)
    target = {}
    inventory = reward_probe._process_inventory()
    if observe:
        game_session = home / game_debug.TEST_SESSION
        game_debug.verify_launch(game_session, game_debug._json(game_session, "manifest.json"), home)
        expected = game_session / game_debug.APP / game_launch.EXECUTABLE
        pid = reward_probe.select_target(inventory, expected, os.getuid())
        target = {"target_pid": pid, "target_game": expected}
    elif list(reward_probe._candidates(inventory)):
        raise HarnessError("Close Steam and all game copies for the login-only test")
    started = time.monotonic()
    cli._validate_launch_copy(session)
    if not (session / "signing.json").is_file():
        raise HarnessError("Controlled access requires the verified signed disposable copy")
    events = []
    with Gateway() as gateway:
        print("Checking the gateway connection with fixed data before opening the companion.", flush=True)
        preflight = sanitized_preflight(gateway.preflight())
        baseline = dict(gateway.counts)
        preflight_failure_count = len(gateway.failure_details)
        remaining = max(0, math.floor(seconds - (time.monotonic() - started)))
        if preflight["passed"] and remaining > 0:
            print("Connection check passed; opening the protected companion.", flush=True)
            report = cli.launch_outer(session, remaining, approved=True, _controlled=gateway, **target)
            report.setdefault("launch", {})["app_started"] = True
            events = sanitized_events(cli.load_events(Path(report["attempt_dir"])))
        else:
            reason = "NOT_ATTEMPTED_PREFLIGHT_FAILED" if not preflight["passed"] else "NOT_ATTEMPTED_TIME_BUDGET"
            report = not_started_report(reason, seconds)
            print("The companion was not opened; the diagnostic below records the connection check.", flush=True)
    if not gateway.cleanup_complete:
        raise HarnessError("Controlled gateway cleanup did not complete")
    if report.get("launch", {}).get("app_started") is not True:
        # A failed preflight may finish recording its error during drain. With
        # no app started, every final request/failure belongs to the preflight.
        baseline = dict(gateway.counts)
        preflight_failure_count = len(gateway.failure_details)
    delta = {key: count - baseline.get(key, 0) for key, count in gateway.counts.items()}
    overflow = gateway.failure_overflow
    safe = {"schema": 1, "mode": "CONTROLLED_MANUAL_OAUTH", "report": sanitized_report(report),
            "events": events, "preflight": preflight, "gateway_counts": safe_counts(delta),
            "preflight_gateway_counts": safe_counts(baseline),
            "gateway_failures": sanitized_failures(gateway.failure_details, preflight_failure_count),
            "gateway_failure_overflow": overflow if type(overflow) is int and 0 <= overflow <= 1000000 else 0,
            "raw_logs_included": False, "account_details_included": False, "gateway_cleanup_complete": True}
    # report/status are harness-generated fixed fields, not raw server/account responses.
    output = tempfile.NamedTemporaryFile(prefix="sts2test-controlled.", suffix=".json", dir="/private/tmp", delete=False)
    with output:
        output.write((json.dumps(safe, indent=2) + "\n").encode())
    os.chmod(output.name, 0o644)
    print("Diagnostic file: " + output.name)
    return safe


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session", type=Path)
    parser.add_argument("--proposal", action="store_true")
    parser.add_argument("--approve-controlled-access", action="store_true")
    parser.add_argument("--observe-debug-game", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = proposal(args.session) if args.proposal else run(args.session, approved=args.approve_controlled_access, observe=args.observe_debug_game)
        print(json.dumps(result, indent=2))
        if args.proposal:
            return 0
        authenticated = any(event.get("event") == "authenticated" for event in result.get("events", []))
        report = result.get("report", {})
        healthy = (result.get("preflight", {}).get("passed") is True
                   and report.get("startup") == "ELECTRON_READY" and report.get("startup_blocker_count", 0) == 0
                   and report.get("launch", {}).get("exit_code") in (None, 0))
        return 0 if authenticated and healthy else 1
    except Exception:
        # Vendor/auth exceptions can embed credentials. Never echo them into shared output.
        print("Controlled probe stopped. Private session logs may contain sensitive account data; do not share them.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
