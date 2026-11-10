"""Opt-in original-fixture task-port experiment; never accepts a target PID."""
import argparse
import hashlib
import json
import os
import platform
import plistlib
import selectors
import subprocess
import sys
import tempfile
from pathlib import Path

from .asar import HarnessError
from .cli import sandbox_profile, stop_probe
from .signing import ENTITLEMENTS

GET_TASK_ALLOW = "com.apple.security.get-task-allow"
GAME_ENTITLEMENTS = {k: v for k, v in ENTITLEMENTS.items() if k != "com.apple.security.cs.debugger"}


def classify(rows):
    """Interpret only a complete, internally consistent 2x2 native matrix."""
    expected = {(target, policy) for target in (False, True) for policy in (False, True)}
    cells = {}
    for row in rows:
        key = (row.get("get_task_allow"), row.get("outer_sandbox"))
        if (type(key[0]) is not bool or type(key[1]) is not bool or key in cells
                or type(row.get("acquired")) is not bool
                or type(row.get("kern_return")) is not int
                or row["acquired"] != (row["kern_return"] == 0)):
            raise HarnessError("Invalid or duplicate native matrix cell")
        cells[key] = row["acquired"]
    if set(cells) != expected:
        raise HarnessError("Incomplete native matrix")
    if not cells[False, False] and not cells[False, True] and cells[True, False] and cells[True, True]:
        return "TARGET_ENTITLEMENT_DISTINGUISHES_FIXTURES"
    if cells[True, False] and not cells[True, True]:
        return "OUTER_POLICY_BLOCKS_ENTITLED_FIXTURE"
    if all(cells.values()):
        return "ALL_FIXTURE_PORTS_ACQUIRED"
    return "INCONCLUSIVE"


def _command(command, environment, cwd, timeout=30):
    try:
        result = subprocess.run(command, env=environment, cwd=cwd, capture_output=True,
                                text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise HarnessError("Diagnostic command unavailable or timed out; no prompt was approved") from exc
    if result.returncode:
        raise HarnessError(f"Diagnostic command failed ({result.returncode}): {result.stderr[-1000:]}")
    return result


def _build(root, source, name, entitlements, environment):
    binary = root / name
    _command(["/usr/bin/clang", "-Wall", "-Wextra", "-Werror", "-Os",
              str(Path(__file__).with_name(source)), "-o", str(binary)], environment, root)
    binary.chmod(0o700)
    plist = root / (name + ".plist")
    plist.write_bytes(plistlib.dumps(entitlements))
    _command(["/usr/bin/codesign", "--force", "--sign", "-", "--options", "runtime",
              "--timestamp=none", "--identifier",
              "local.untapped-harness." + ("target" if source == "attachment_target.c" else "inspector"),
              "--entitlements", str(plist), str(binary)], environment, root)
    _command(["/usr/bin/codesign", "--verify", "--strict", str(binary)], environment, root)
    actual = _command(["/usr/bin/codesign", "-d", "--entitlements", ":-", str(binary)], environment, root)
    if plistlib.loads(actual.stdout.encode()) != entitlements:
        raise HarnessError("Fixture entitlements differ from requested settings")
    metadata = _command(["/usr/bin/codesign", "-dvv", str(binary)], environment, root)
    if "runtime)" not in metadata.stderr or "Signature=adhoc" not in metadata.stderr:
        raise HarnessError("Fixture is not ad-hoc Hardened Runtime")
    return binary


def _ready(process):
    with selectors.DefaultSelector() as selector:
        selector.register(process.stdout, selectors.EVENT_READ)
        if not selector.select(timeout=3):
            raise HarnessError("Fixture readiness timed out")
        data = os.read(process.stdout.fileno(), 256)
    try:
        ready = json.loads(data)
    except (ValueError, UnicodeError) as exc:
        raise HarnessError("Invalid fixture readiness") from exc
    if ready != {"pid": process.pid, "uid": os.getuid()} or process.poll() is not None:
        raise HarnessError("Fixture identity/readiness mismatch")


def run():
    if platform.system() != "Darwin" or os.getuid() == 0 or os.getuid() != os.geteuid():
        raise HarnessError("Diagnostic requires unprivileged macOS execution")
    root = Path(tempfile.mkdtemp(prefix="untapped-attachment-diagnostic-", dir="/private/tmp"))
    root.chmod(0o700)
    environment = {"PATH": "/usr/bin:/bin", "LANG": "C", "TMPDIR": str(root)}
    report = {"schema": 1, "scope": "ORIGINAL_FIXTURES_ONLY", "session": str(root), "rows": [],
              "memory_read_or_write": False, "game_or_companion_modified": False,
              "uid": os.getuid()}
    processes = []
    try:
        targets = {enabled: _build(root, "attachment_target.c", "target-" + str(int(enabled)),
                    {**GAME_ENTITLEMENTS, **({GET_TASK_ALLOW: True} if enabled else {})}, environment)
                   for enabled in (False, True)}
        inspector = _build(root, "attachment_inspector.c", "inspector", ENTITLEMENTS, environment)
        policy_text = (sandbox_profile(root, Path.home().resolve())
                       + '\n(allow network* (subpath ' + json.dumps(str(root)) + '))\n')
        policy = root / "outer.sb"
        policy.write_text(policy_text)
        report["policy_sha256"] = hashlib.sha256(policy_text.encode()).hexdigest()
        report["fixture_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                     for p in (*targets.values(), inspector)}
        for enabled, target in targets.items():
            process = subprocess.Popen([str(target)], cwd=root, env=environment,
                                       stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                       start_new_session=True)
            processes.append(process)
            _ready(process)
            for sandboxed in (False, True):
                command = [str(inspector), str(process.pid), str(target)]
                if sandboxed:
                    command = ["/usr/bin/sandbox-exec", "-f", str(policy), *command]
                result = _command(command, environment, root, timeout=5)
                try:
                    row = json.loads(result.stdout)
                except ValueError as exc:
                    raise HarnessError("Inspector returned invalid JSON") from exc
                if (row.get("pid") != process.pid or row.get("uid") != os.getuid()
                        or process.poll() is not None):
                    raise HarnessError("Target identity/liveness changed during inspection")
                report["rows"].append({**row, "get_task_allow": enabled, "outer_sandbox": sandboxed})
        report["conclusion"] = classify(report["rows"])
    except Exception as exc:
        report["conclusion"] = "EXPERIMENT_FAILED"
        report["error"] = str(exc)[:1200]
        raise HarnessError(str(exc) + "; diagnostic report: " + str(root / "report.json")) from exc
    finally:
        active_error = sys.exc_info()[0] is not None
        cleanup_errors = []
        for process in processes:
            try:
                stop_probe(process)
            except Exception as exc:
                cleanup_errors.append(str(exc)[:300])
            finally:
                try:
                    process.stdout.close()
                except OSError as exc:
                    cleanup_errors.append(str(exc)[:300])
        report["targets_stopped"] = all(p.poll() is not None for p in processes)
        if cleanup_errors or not report["targets_stopped"]:
            report["conclusion"] = "EXPERIMENT_FAILED"
            report["cleanup_errors"] = cleanup_errors or ["Fixture remains running"]
        output = root / "report.json"
        output.write_text(json.dumps(report, indent=2) + "\n")
        output.chmod(0o600)
        if report.get("cleanup_errors") and not active_error:
            raise HarnessError("Fixture cleanup failed; inspect " + str(output))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-original-fixtures", action="store_true", required=True)
    parser.parse_args()
    try:
        print(json.dumps(run(), indent=2))
    except (HarnessError, OSError, ValueError) as exc:
        parser.exit(2, str(exc) + "\n")


if __name__ == "__main__":
    main()
