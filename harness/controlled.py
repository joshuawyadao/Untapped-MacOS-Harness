"""Prepare and supervise manual OAuth/public-data experiments; no login automation."""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from . import cli, game_debug, game_launch, reward_probe
from .asar import HarnessError, sha256
from .gateway import Gateway

EVENTS = {"bootstrap", "ready", "window-detected", "attach-attempt", "reader-connected",
          "reward", "manual-sign-in-ready", "authenticated"}


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
            "live_network_attempted": False, "requires_explicit_approval": True}


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
                                   "raw_logs_private", "post_auth_limit", "authenticated_event_observed"}
                        and (value is None or type(value) in (int, bool))}
    return result


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
    with Gateway() as gateway:
        report = cli.launch_outer(session, seconds, approved=True, _controlled=gateway, **target)
        events = sanitized_events(cli.load_events(Path(report["attempt_dir"])))
    if not gateway.cleanup_complete:
        raise HarnessError("Controlled gateway cleanup did not complete")
    counts = [{"route": route, "status": status, "count": count}
              for (route, status), count in sorted(gateway.counts.items())]
    safe = {"schema": 1, "mode": "CONTROLLED_MANUAL_OAUTH", "report": sanitized_report(report),
            "events": events, "gateway_counts": counts,
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
        healthy = (report.get("startup") == "ELECTRON_READY" and report.get("startup_blocker_count", 0) == 0
                   and report.get("launch", {}).get("exit_code") in (None, 0))
        return 0 if authenticated and healthy else 1
    except (HarnessError, OSError, ValueError, KeyError, subprocess.SubprocessError):
        # Vendor/auth exceptions can embed credentials. Never echo them into shared output.
        print("Controlled probe stopped. Private session logs may contain sensitive account data; do not share them.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
