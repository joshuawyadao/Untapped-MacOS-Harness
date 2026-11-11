"""Supervise a signed Untapped copy beside one identified native game process."""

import json
import os
import platform
import pwd
import re
import shlex
import shutil
import stat
import subprocess
import tempfile
import time
from pathlib import Path

from . import cli, controlled, main_account, main_preferences, process_identity
from .asar import HarnessError, sha256
from .gateway import Gateway

MAX_SECONDS = 8 * 3600
EVENT_NAMES = controlled.EVENTS | {"main-steam-verified", "main-steam-mismatch"}
STOP_REASONS = {"GAME_EXIT", "GAME_CRASHED", "TARGET_CONFLICT", "OWNER_STOP"}


def _private_directory(path):
    path = Path(path)
    try:
        if not path.is_absolute() or path.resolve(strict=True) != path:
            raise HarnessError("Main-account path is not canonical")
        info = path.lstat()
    except (OSError, RuntimeError) as exc:
        raise HarnessError("Main-account directory is unavailable") from exc
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise HarnessError("Main-account directory must be owned mode 0700")
    return path


def _target_environment(pid, executable):
    if type(pid) is not int or pid <= 0:
        raise HarnessError("Target game PID must be positive")
    executable = Path(executable)
    try:
        if not executable.is_absolute() or executable.resolve(strict=True) != executable:
            raise HarnessError("Target game path is not canonical")
        info = executable.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise HarnessError("Target game executable has an unexpected owner or type")
        result = subprocess.run(["/bin/ps", "-p", str(pid), "-o", "uid=,comm="],
                                capture_output=True, text=True, timeout=2, check=True)
        row = result.stdout.strip().split(None, 1)
        if len(row) != 2 or row != [str(os.getuid()), str(executable)]:
            raise HarnessError("Target game process identity changed")
    except (OSError, subprocess.SubprocessError) as exc:
        raise HarnessError("Target game process identity could not be verified") from exc
    return {"UNTAPPED_HARNESS_TARGET_PID": str(pid),
            "UNTAPPED_HARNESS_TARGET_EXECUTABLE": str(executable),
            "UNTAPPED_HARNESS_TARGET_UID": str(os.getuid())}


def _events(attempt):
    # No arbitrary payload, identifiers, or log text crosses into the public report.
    result = set()
    path = attempt / "profile/events.jsonl"
    try:
        parent = main_account._open_directory(path.parent, os.getuid())
        try:
            fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        finally:
            os.close(parent)
    except FileNotFoundError:
        return result
    except OSError as exc:
        raise HarnessError("Private event stream cannot be read safely") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
            raise HarnessError("Private event stream has unsafe attributes")
        start = max(0, info.st_size - 1024 * 1024)
        os.lseek(fd, start, os.SEEK_SET)
        raw = os.read(fd, min(info.st_size - start, 1024 * 1024))
        if start:
            raw = raw.partition(b"\n")[2]
    finally:
        os.close(fd)
    for line in raw.splitlines():
        if len(line) > 65536:
            continue
        try:
            row = json.loads(line)
        except (ValueError, UnicodeError, RecursionError):
            continue
        if isinstance(row, dict) and isinstance(row.get("event"), str) and row["event"] in EVENT_NAMES:
            result.add(row["event"])
    return result


def supervise(process, attempt, seconds, should_stop=None, *, clock=time.monotonic):
    """Poll the owned companion only. Authentication never shortens the run."""
    if seconds is None and not callable(should_stop):
        raise HarnessError("Unlimited companion supervision requires a stop callback")
    deadline = None if seconds is None else clock() + seconds
    seen = set()
    while True:
        seen.update(_events(attempt))
        if "main-steam-mismatch" in seen:
            return "STEAM_ACCOUNT_MISMATCH", seen
        if should_stop is not None:
            reason = should_stop()
            if reason is not None:
                if reason not in STOP_REASONS:
                    raise HarnessError("Unexpected game-stop result")
                return reason, seen
        exit_code = process.poll()
        if exit_code is not None:
            seen.update(_events(attempt))
            return ("COMPANION_EXITED" if exit_code == 0 else "COMPANION_CRASHED"), seen
        remaining = None if deadline is None else deadline - clock()
        if remaining is not None and remaining <= 0:
            return "SESSION_LIMIT_REACHED", seen
        try:
            process.wait(timeout=0.5 if remaining is None else min(0.5, remaining))
        except subprocess.TimeoutExpired:
            pass


def _clone(session, manifest):
    root = Path(tempfile.mkdtemp(prefix=f"uc-sts2-main-{os.getuid()}-", dir="/private/tmp"))
    _private_directory(root)
    try:
        shutil.copytree(session / "Companion.app", root / "Companion.app", symlinks=True)
        for filename in ("manifest.json", "signing.json"):
            source = session / filename
            if source.is_symlink() or not source.is_file():
                raise HarnessError("Signed companion receipt is missing")
            shutil.copy2(source, root / filename, follow_symlinks=False)
        (root / "profile").mkdir(mode=0o700)
        (root / "t").mkdir(mode=0o700)
        (root / "profile/temp").mkdir(mode=0o700)
        (root / "profile/cache").mkdir(mode=0o700)
        (root / "profile/sessionData").mkdir(mode=0o700)
        cli._validate_launch_copy(root)
        if manifest.get("controlled_access_version") != 1:
            raise HarnessError("Companion lacks controlled access")
        return root
    except BaseException:
        shutil.rmtree(root)
        raise


def _launch(root, gateway, target_environment, expected_steam_id, expected_profile, remember=None):
    profile = root / "profile"
    helper = profile / "controlled-network.cjs"
    adapter = Path(__file__).with_name("controlled_network.cjs").read_bytes()
    manifest = cli.read_json(root / "manifest.json")
    if sha256(adapter) != manifest.get("controlled_network_sha256"):
        raise HarnessError("Controlled adapter changed since companion preparation")
    helper.write_bytes(adapter)
    helper.chmod(0o600)
    probe = process_identity.prepare_identity_probe(profile)
    environment = cli.launch_environment(root)
    environment.update(target_environment)
    environment.update({
        "UNTAPPED_HARNESS_IDENTITY_SHA256": probe["sha256"],
        "UNTAPPED_HARNESS_CONTROLLED_ACCESS": "1",
        "UNTAPPED_HARNESS_GATEWAY_URL": gateway.url,
        "UNTAPPED_HARNESS_GATEWAY_KEY": gateway.key,
        "UNTAPPED_HARNESS_NETWORK_SHA256": sha256(adapter),
        "UNTAPPED_HARNESS_MAIN_ACCOUNT": "1",
        "UNTAPPED_HARNESS_EXPECTED_STEAM_ID": expected_steam_id,
        "UNTAPPED_HARNESS_EXPECTED_PROFILE": str(expected_profile),
    })
    if remember is not None:
        login_helper = Path(__file__).with_name("remember_keytar.cjs").read_bytes()
        if (manifest.get("remember_login_version") != 1
                or manifest.get("remember_login_helper_sha256") != sha256(login_helper)):
            raise HarnessError("Companion lacks the reviewed remember-login bridge")
        target = profile / "remember-keytar.cjs"
        target.write_bytes(login_helper)
        target.chmod(0o600)
        environment.update(remember.environment)
        environment.update({"UNTAPPED_HARNESS_REMEMBER_LOGIN": "1",
                            "UNTAPPED_HARNESS_LOGIN_HELPER_SHA256": sha256(login_helper)})
    policy = root / "controlled.sb"
    real_home = Path(pwd.getpwuid(os.getuid()).pw_dir).resolve(strict=True)
    policy.write_text(cli.sandbox_profile(root, real_home)
                      + "\n(allow network* (subpath " + json.dumps(str(root)) + "))\n")
    policy.chmod(0o600)
    print("Manual sign-in URL will be written privately to: " + str(profile / "manual-sign-in-url.txt"), flush=True)
    print("After Sign In, run in another Terminal: cat " + shlex.quote(str(profile / "manual-sign-in-url.txt")), flush=True)
    print("Use the companion Sign In button, then open the URL manually. Do not share the URL or raw logs.", flush=True)
    command = ["/usr/bin/sandbox-exec", "-f", str(policy),
               str(root / "Companion.app/Contents/MacOS/Untapped.gg Companion"),
               "--user-data-dir=" + str(profile), "--no-sandbox"]
    output = (root / "stdout.log").open("xb")
    try:
        process = subprocess.Popen(command, cwd=root, env=environment,
                                   stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
    finally:
        output.close()
    return process


def _diagnostic(safe):
    fd, path = tempfile.mkstemp(prefix="sts2main-controlled.", suffix=".json", dir="/private/tmp")
    try:
        os.fchmod(fd, 0o644)
        with os.fdopen(fd, "w") as stream:
            json.dump(safe, stream, indent=2)
            stream.write("\n")
    except BaseException:
        os.unlink(path)
        raise
    print("Diagnostic file: " + path, flush=True)


def run(session: Path, preferences_dir: Path, *, target_pid: int, target_game: Path,
        expected_steam_id: str, expected_profile: int, seconds=14400,
        should_stop=None, on_companion_ready=None, remember_store=None):
    """Start one private signed copy; never signal or modify the game process."""
    if platform.system() != "Darwin" or os.getuid() == 0 or os.getuid() != os.geteuid():
        raise HarnessError("Main-account companion requires unprivileged macOS")
    if seconds is not None and (type(seconds) is not int or not 1 <= seconds <= MAX_SECONDS):
        raise HarnessError("Companion duration must be 1–28800 seconds")
    if seconds is None and not callable(should_stop):
        raise HarnessError("Unlimited companion run requires a stop callback")
    if not isinstance(expected_steam_id, str) or not re.fullmatch(r"[0-9]{1,20}", expected_steam_id):
        raise HarnessError("Expected Steam identity is invalid")
    if type(expected_profile) is not int or not 0 <= expected_profile <= 99:
        raise HarnessError("Expected game profile is invalid")
    session = _private_directory(session)
    preferences_dir = _private_directory(preferences_dir)
    target_environment = _target_environment(target_pid, target_game)
    controlled.proposal(session)  # Verifies gateway and adapter against the prepared manifest.
    _, manifest, _ = cli._validate_launch_copy(session)
    if manifest.get("main_steam_guard_version") != 1:
        raise HarnessError("Companion lacks the prepared Steam identity guard")
    if not (session / "signing.json").is_file():
        raise HarnessError("Main-account launch requires a signed companion")
    started = time.monotonic()
    root = None
    process = None
    login_bridge = None
    gateway = None
    reason = "PREFLIGHT_FAILED"
    failure_stage = "NONE"
    stage = "gateway"
    seen = set()
    terminated = False
    companion_exit_code = None
    group_cleanup_complete = True
    saved = False
    removed = False
    preflight = {"passed": False, "results": [], "requests_attempted": 0,
                 "maximum_requests": 2, "real_credentials_sent": False}
    baseline = {}
    preflight_failures = 0
    try:
        gateway = Gateway()
        with gateway:
            try:
                stage = "preflight"
                preflight = controlled.sanitized_preflight(gateway.preflight())
                baseline = dict(gateway.counts)
                preflight_failures = len(gateway.failure_details)
                if preflight["passed"] and (seconds is None or time.monotonic() - started < seconds):
                    stage = "clone"
                    root = _clone(session, manifest)
                    stage = "seed"
                    main_preferences.seed(root / "profile", preferences_dir,
                                          enable_default_tiers=manifest.get("ui_assets_version") in (1, 2))
                    stage = "launch"
                    if remember_store is not None:
                        from .remember_login import RememberBroker
                        login_bridge = RememberBroker(root, remember_store,
                            on_warning=getattr(remember_store, "on_warning", None))
                        login_bridge.__enter__()
                        process = _launch(root, gateway, target_environment,
                                          expected_steam_id, expected_profile, remember=login_bridge)
                    else:
                        process = _launch(root, gateway, target_environment,
                                          expected_steam_id, expected_profile)
                    if on_companion_ready is not None:
                        on_companion_ready(root)
                    stage = "supervise"
                    remaining = None if seconds is None else seconds - (time.monotonic() - started)
                    reason, seen = supervise(process, root, remaining,
                                             should_stop)
                    if reason == "GAME_CRASHED":
                        failure_stage = "GAME_PROCESS_EXIT"
                elif preflight["passed"]:
                    reason = "SESSION_LIMIT_REACHED"
            except KeyboardInterrupt:
                reason = "INTERRUPTED"
                failure_stage = stage.upper()
            except Exception:
                reason = "COMPANION_FAILED"
                failure_stage = stage.upper()
            finally:
                if process is not None:
                    # Helpers may outlive an exited main process. Always reap the owned group.
                    try:
                        companion_exit_code = process.poll()
                        terminated = companion_exit_code is None
                        if companion_exit_code not in (None, 0) and failure_stage == "NONE":
                            reason = "COMPANION_CRASHED"
                            failure_stage = "PROCESS_EXIT"
                        cli.stop_probe(process)
                    except (Exception, KeyboardInterrupt):
                        group_cleanup_complete = False
                        reason = "COMPANION_CLEANUP_FAILED"
                        failure_stage = "GROUP_CLEANUP"
                    if group_cleanup_complete:
                        try:
                            seen.update(_events(root))
                        except Exception:
                            if failure_stage == "NONE":
                                reason = "COMPANION_FAILED"
                                failure_stage = "EVENT_READ"
                        try:
                            main_preferences.harvest(root / "profile", preferences_dir)
                            saved = True
                        except Exception:
                            reason = "COMPANION_FAILED"
                            failure_stage = "HARVEST"
                if login_bridge is not None:
                    try:
                        login_bridge.close()
                    except Exception:
                        reason = "COMPANION_FAILED"
                        failure_stage = "LOGIN_BRIDGE_CLEANUP"
                if root is not None and failure_stage == "NONE":
                    try:
                        # Only this exact private attempt root may be removed.
                        if not root.name.startswith(f"uc-sts2-main-{os.getuid()}-"):
                            raise HarnessError("Unexpected private companion root")
                        shutil.rmtree(root)
                        removed = True
                    except Exception:
                        reason = "COMPANION_FAILED"
                        failure_stage = "ATTEMPT_CLEANUP"
    except KeyboardInterrupt:
        reason = "INTERRUPTED"
        failure_stage = "GATEWAY"
    except Exception:
        reason = "COMPANION_FAILED"
        failure_stage = "GATEWAY"
    gateway_cleanup_complete = gateway is not None and gateway.cleanup_complete is True
    if not gateway_cleanup_complete:
        reason = "GATEWAY_CLEANUP_FAILED"
        failure_stage = "GATEWAY_CLEANUP"
    counts = gateway.counts if gateway is not None else {}
    if process is None:
        baseline = dict(counts)
        preflight_failures = len(gateway.failure_details) if gateway is not None else 0
    delta = {key: count - baseline.get(key, 0) for key, count in counts.items()}
    overflow = getattr(gateway, "failure_overflow", 0)
    safe = {"schema": 1, "mode": "MAIN_ACCOUNT_CONTROLLED_COMPANION",
            "reason": reason, "failure_stage": failure_stage, "preflight": preflight,
            "companion_started": process is not None, "companion_terminated": terminated,
            "companion_exit_code": companion_exit_code,
            "companion_group_cleanup_complete": group_cleanup_complete,
            "authenticated": "authenticated" in seen,
            "steam_account_verified": "main-steam-verified" in seen and "main-steam-mismatch" not in seen,
            "reward_observed": "reward" in seen, "overlay_show_recorded": "overlay-show" in seen,
            "preferences_saved": saved, "private_attempt_removed": removed,
            "private_attempt_retained": root is not None and not removed,
            "gateway_counts": controlled.safe_counts(delta),
            "preflight_gateway_counts": controlled.safe_counts(baseline),
            "gateway_failures": controlled.sanitized_failures(
                gateway.failure_details if gateway is not None else [], preflight_failures),
            "gateway_failure_overflow": overflow if type(overflow) is int and 0 <= overflow <= 1000000 else 0,
            "gateway_cleanup_complete": gateway_cleanup_complete,
            "raw_logs_included": False, "account_details_included": False}
    _diagnostic(safe)
    if root is not None and not removed:
        print("Private companion attempt retained locally: " + str(root), flush=True)
    return safe
