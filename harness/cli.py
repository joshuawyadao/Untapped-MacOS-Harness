"""Inspect, prepare, and diagnose a user-supplied macOS Untapped companion."""
import argparse
import json
import math
import os
import platform
import plistlib
import shutil
import signal
import subprocess
import sys
from pathlib import Path

from .asar import Archive, HarnessError, sha256
from .patches import (ASAR_SHA256, VERSION, OVERLAY, RUNTIME, SCRY, SCRY_SHA256,
                      EXECUTABLE_SHA256, FRAMEWORK_SHA256, patched_entries)
from .signing import (signing_proposal, sign_copy, expected_executable_hash, verify_signed_copy)

ROOT = Path(__file__).resolve().parents[1]
FUSE_SENTINEL = b"dL7pKGdnNz796PbbjQWNKmHXBZaB9tsX"


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def read_json(path):
    return json.loads(path.read_text())


def inspect_app(app):
    app = app.resolve(strict=True)
    contents = app / "Contents"
    archive_bytes = (contents / "Resources/app.asar").read_bytes()
    if sha256(archive_bytes) != ASAR_SHA256:
        raise HarnessError("Unsupported archive hash; re-inspect a new release before changing pins")
    archive = Archive(archive_bytes)
    plist = plistlib.loads((contents / "Info.plist").read_bytes())
    if plist.get("CFBundleShortVersionString") != VERSION:
        raise HarnessError("Companion version mismatch")
    patched_entries(archive)  # All anchors must match before any copy or mutation.
    for path in (OVERLAY, RUNTIME):
        archive.read(path)
    native = contents / "Resources/app.asar.unpacked" / SCRY
    framework = contents / "Frameworks/Electron Framework.framework/Versions/A/Electron Framework"
    executable = contents / "MacOS/Untapped.gg Companion"
    wire_bytes = framework.read_bytes()
    if (sha256(native.read_bytes()) != SCRY_SHA256 or sha256(wire_bytes) != FRAMEWORK_SHA256
            or sha256(executable.read_bytes()) != EXECUTABLE_SHA256):
        raise HarnessError("Native reader or Electron binary hash mismatch")
    wires = []
    position = 0
    while True:
        position = wire_bytes.find(FUSE_SENTINEL, position)
        if position < 0:
            break
        start = position + len(FUSE_SENTINEL)
        version, length = wire_bytes[start:start + 2]
        wire = wire_bytes[start + 2:start + 2 + length].decode("ascii")
        wires.append({"version": version, "wire": wire})
        position = start
    if wires != [{"version": 1, "wire": "10110001"}] * 2:
        raise HarnessError("Unexpected Electron fuse configuration")
    report = {
        "companion_version": VERSION, "app_asar_sha256": ASAR_SHA256,
        "asar_header_sha256": sha256(archive.raw_header),
        "plist_header_hash_matches": plist.get("ElectronAsarIntegrity", {}).get(
            "Resources/app.asar", {}).get("hash") == sha256(archive.raw_header),
        "native_scry_sha256": sha256(native.read_bytes()), "electron_fuses": wires,
        "guarded_patches_match": True, "runtime": "UNTESTED",
    }
    if platform.system() == "Darwin":
        result = subprocess.run(["/usr/bin/codesign", "--verify", "--deep", "--strict", str(app)],
                                capture_output=True, text=True)
        report["source_signature_valid"] = result.returncode == 0
    return report, archive, plist


def prepare(app, destination):
    app = app.resolve(strict=True)
    destination = destination.parent.resolve(strict=True) / destination.name
    if destination.exists() or destination.is_symlink():
        raise HarnessError("Session destination must be new")
    if destination.is_relative_to(ROOT) or destination.is_relative_to(app):
        raise HarnessError("Keep disposable vendor copies outside the repository and source app")
    report, archive, _ = inspect_app(app)
    if platform.system() == "Darwin" and not report.get("source_signature_valid"):
        raise HarnessError("Source vendor signature is invalid; use a pristine official app")
    replacements = patched_entries(archive)
    patched_bytes = archive.rewrite(replacements)
    # Round-trip verify the rewritten offsets and content before touching disk.
    rewritten = Archive(patched_bytes)
    for path, content in replacements.items():
        if rewritten.read(path) != content:
            raise HarnessError("ASAR round-trip mismatch")
    destination.mkdir(mode=0o700)
    copy = destination / "Companion.app"
    shutil.copytree(app, copy, symlinks=True)
    target = copy / "Contents/Resources/app.asar"
    if target.is_symlink():
        raise HarnessError("Refusing to write through an ASAR symlink")
    # Atomic replacement cannot write through a resource hard link to the source.
    temporary = target.with_suffix(".harness-tmp")
    temporary.write_bytes(patched_bytes)
    os.replace(temporary, target)
    (destination / "profile").mkdir(mode=0o700)
    report.update({
        "schema": 1, "patched_asar_sha256": sha256(patched_bytes),
        "patched_entries": sorted(replacements), "vendor_bundle_seal": "INVALIDATED_BY_RESOURCE_PATCH",
        "signing_changed": False, "game_modified": False,
        "startup": "UNTESTED", "attachment": "UNTESTED", "state_reading": "UNTESTED",
        "overlay": "UNTESTED", "reward_comparison": "UNTESTED",
    })
    write_json(destination / "manifest.json", report)
    return report


def sandbox_profile(session, real_home):
    # SBPL strings use JSON-compatible quoting for these absolute local paths.
    return '\n'.join([
        '(version 1)', '(allow default)', '(deny network*)',
        '(allow network-inbound (local ip "localhost:*"))',
        '(allow network-outbound (remote ip "localhost:*"))',
        '(deny file-write*)',
        f'(deny file-read* (subpath {json.dumps(str(real_home))}))',
        f'(allow file-read* file-write* (subpath {json.dumps(str(session))}))',
        '(allow file-write* (literal "/dev/null"))',
        '(deny mach-lookup (global-name "com.apple.securityd"))', '',
    ])


def launch_environment(session):
    # Construct from scratch: no SUDO_USER, NODE_OPTIONS, API overrides, or credentials.
    return {
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "LANG": "en_US.UTF-8", "NODE_ENV": "production",
        "TMPDIR": str(session / "profile/temp"), "UC_TEST_SANDBOX_DIR": str(session / "profile"),
        "UC_TEST_SANDBOX_ID": "native-sts2-harness", "UC_SKIP_UPDATE_CHECKS": "1",
        "UNTAPPED_HARNESS_OFFLINE": "1",
    }


def stop_probe(process):
    """Terminate the whole probe group even when its leader exits first."""
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass
    # A reader/renderer may outlive its parent or ignore SIGTERM.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()


def launch(session, seconds):
    if platform.system() != "Darwin":
        raise HarnessError("Launch requires macOS with sandbox-exec; there is no unsandboxed fallback")
    session = session.resolve(strict=True)
    report = read_json(session / "manifest.json")
    app = session / "Companion.app"
    if sha256((app / "Contents/Resources/app.asar").read_bytes()) != report["patched_asar_sha256"]:
        raise HarnessError("Prepared archive changed; create a new session")
    binary_pins = {
        "MacOS/Untapped.gg Companion": expected_executable_hash(session, report),
        "Frameworks/Electron Framework.framework/Versions/A/Electron Framework": FRAMEWORK_SHA256,
        "Resources/app.asar.unpacked/" + SCRY: SCRY_SHA256,
    }
    for relative, expected in binary_pins.items():
        if sha256((app / "Contents" / relative).read_bytes()) != expected:
            raise HarnessError("Prepared native binary changed; create a new session")
    if (session / "profile").resolve() != session / "profile":
        raise HarnessError("Profile must not be a symlink to shared settings or saves")
    if (session / "signing.json").exists():
        verify_signed_copy(session)
    # No silent continuation after terms: each CLI session is a single fresh startup probe.
    if (session / "launch.json").exists():
        raise HarnessError("Startup probes are single-use; prepare a fresh session")
    for directory in ("temp", "cache", "sessionData"):
        (session / "profile" / directory).mkdir(exist_ok=True)
    policy = session / "offline.sb"
    policy.write_text(sandbox_profile(session, Path.home().resolve()))
    exe = app / "Contents/MacOS/Untapped.gg Companion"
    command = ["/usr/bin/sandbox-exec", "-f", str(policy), str(exe),
               "--user-data-dir=" + str(session / "profile")]
    # The session path is local-only. Output may contain vendor diagnostics; never commit it.
    result = {"startup": "ATTEMPTED", "seconds_limit": seconds, "network": "LOOPBACK_ONLY"}
    write_json(session / "launch.json", result)
    with (session / "stdout.log").open("wb") as output:
        process = subprocess.Popen(command, cwd=session, env=launch_environment(session),
                                   stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            result["exit_code"] = process.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            result["time_limit_reached"] = True
        finally:
            # Close only this probe and its descendants, never another companion or game.
            stop_probe(process)
    write_json(session / "launch.json", result)
    return status(session)


def load_events(session):
    path = session / "profile/events.jsonl"
    if not path.exists():
        return []
    if path.stat().st_size > 2 * 1024 * 1024:
        raise HarnessError("Diagnostic events exceed the bounded input limit")
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def status(session):
    events = load_events(session)
    names = {event.get("event") for event in events}
    log_path = session / "profile/log.log"
    terms_seen = log_path.exists() and "[Core] Showing Terms of Service" in log_path.read_text(errors="replace")
    return {
        "static_inspection": "VERIFIED" if (session / "manifest.json").exists() else "UNTESTED",
        "startup": "ELECTRON_READY" if "ready" in names else "BOOTSTRAP_ONLY" if "bootstrap" in names else "NOT_OBSERVED",
        "window_detection": "OBSERVED" if "window-detected" in names else "UNTESTED",
        "attachment": "CONNECT_ACKNOWLEDGED" if "reader-connected" in names else "ATTEMPTED" if "attach-attempt" in names else "UNTESTED",
        "state_reading": "REWARD_EVENT_OBSERVED" if "reward" in names else "UNTESTED",
        "overlay": "UNTESTED_REQUIRES_VISUAL_CHECK",
        "reward_comparison": "UNTESTED_USE_COMPARE_REWARD",
        "terms_screen_logged": terms_seen,
        "launch": read_json(session / "launch.json") if (session / "launch.json").exists() else None,
    }


def validate_cards(cards):
    if not isinstance(cards, list) or not 1 <= len(cards) <= 20:
        raise HarnessError("Reward must contain 1–20 cards")
    keys = ("cx", "cy", "width", "height")
    for card in cards:
        if not isinstance(card, dict) or not isinstance(card.get("id"), str) or not card["id"]:
            raise HarnessError("Each reward card needs an ID")
        if type(card.get("upgradeLevel")) is not int or card["upgradeLevel"] < 0:
            raise HarnessError("Each reward card needs a nonnegative integer upgradeLevel")
        for key in keys:
            value = card.get(key)
            if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
                raise HarnessError("Reward geometry must be finite normalized coordinates")
        if card["width"] <= 0 or card["height"] <= 0:
            raise HarnessError("Reward card dimensions must be positive")
    return sorted(cards, key=lambda card: (card["cx"], card["cy"]))


def compare_reward(events, expected, reward_index):
    rewards = [(i, event) for i, event in enumerate(events) if event.get("event") == "reward"]
    if reward_index < 0 or reward_index >= len(rewards):
        raise HarnessError("No reward at the requested zero-based index")
    position, reward = rewards[reward_index]
    required = ["bootstrap", "ready", "window-detected", "attach-attempt", "reader-connected"]
    cursor = 0
    for event in events[:position]:
        if cursor < len(required) and event.get("event") == required[cursor]:
            cursor += 1
    if cursor != len(required):
        raise HarnessError("Reward lacks preceding startup/detection/connection evidence")
    actual = validate_cards(reward.get("cards"))
    wanted = validate_cards(expected.get("cards"))
    differences = []
    if len(actual) != len(wanted):
        differences.append("card count")
    for i, (left, right) in enumerate(zip(actual, wanted)):
        for key in ("id", "upgradeLevel"):
            if left[key] != right[key]:
                differences.append(f"card {i}: {key}")
        for key in ("cx", "cy", "width", "height"):
            if abs(left[key] - right[key]) > 0.03:
                differences.append(f"card {i}: {key}")
    return {"reward_index": reward_index, "matches": not differences, "differences": differences,
            "overlay": "UNTESTED_REQUIRES_VISUAL_CHECK", "recommendations": "UNTESTED"}


def main(argv=None):
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    inspect_parser = sub.add_parser("inspect", help="Verify pinned archive without running vendor code")
    inspect_parser.add_argument("app", type=Path)
    prep = sub.add_parser("prepare", help="Create a fresh disposable patched companion session")
    prep.add_argument("app", type=Path)
    prep.add_argument("session", type=Path)
    proposal = sub.add_parser("signing-proposal", help="Describe a per-copy signing change without executing it")
    proposal.add_argument("session", type=Path)
    sign = sub.add_parser("sign-copy", help="Only after explicit owner approval: ad-hoc sign the outer companion")
    sign.add_argument("session", type=Path)
    sign.add_argument("--approve-ad-hoc-signing", action="store_true")
    start = sub.add_parser("launch", help="Run one bounded offline startup probe; never starts the game")
    start.add_argument("session", type=Path)
    start.add_argument("--seconds", type=int, default=20, choices=range(1, 61), metavar="1..60")
    report = sub.add_parser("status")
    report.add_argument("session", type=Path)
    compare = sub.add_parser("compare-reward")
    compare.add_argument("session", type=Path)
    compare.add_argument("expected", type=Path)
    compare.add_argument("--reward-index", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            result = inspect_app(args.app)[0]
        elif args.command == "prepare":
            result = prepare(args.app, args.session)
        elif args.command == "signing-proposal":
            result = signing_proposal(args.session)
        elif args.command == "sign-copy":
            result = sign_copy(args.session, approved=args.approve_ad_hoc_signing)
        elif args.command == "launch":
            result = launch(args.session, args.seconds)
        elif args.command == "status":
            result = status(args.session)
        else:
            result = compare_reward(load_events(args.session), read_json(args.expected), args.reward_index)
        print(json.dumps(result, indent=2))
        failed_startup = args.command == "launch" and result.get("startup") != "ELECTRON_READY"
        return 1 if result.get("matches") is False or failed_startup else 0
    except (HarnessError, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f"Harness stopped: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
