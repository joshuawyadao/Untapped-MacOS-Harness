"""Bounded, offline launch of an unchanged STS2 copy in a separate macOS account."""
import argparse
import hashlib
import grp
import json
import os
import platform
import pwd
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from .asar import HarnessError
from .cli import ROOT, stop_probe

VERSION = "v0.107.1"
COMMIT = "59260271"
ASSEMBLY_HASH = "e7ceb80669bfaf5c8fccabaa126ae2bb283aba514be5b5b55612579cfd285f18"
ASSEMBLY = "Contents/Resources/data_sts2_macos_arm64/sts2.dll"
EXECUTABLE = "Contents/MacOS/Slay the Spire 2"
PROTECTED_HOME = Path("/Users/joshuawyadao")
EXPECTED_TEST_USER = "sts2test"


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def private_path(path, home):
    path = Path(path).absolute()
    if path.is_symlink() or path.resolve() != path or not path.is_relative_to(home):
        raise HarnessError("Test paths must be real paths inside the test account home")
    return path


def test_identity(test_user, original_home):
    if platform.system() != "Darwin" or os.getuid() == 0:
        raise HarnessError("Run as a non-root macOS test account")
    name = pwd.getpwuid(os.getuid()).pw_name
    home = Path(pwd.getpwuid(os.getuid()).pw_dir).resolve(strict=True)
    original = Path(original_home).resolve(strict=True)
    if (name != test_user or name != EXPECTED_TEST_USER or original != PROTECTED_HOME.resolve(strict=True)
            or home == original or home.is_relative_to(original) or original.is_relative_to(home)):
        raise HarnessError("Test user/home must differ from the normal account")
    admin_gid = grp.getgrnam("admin").gr_gid
    if admin_gid in {os.getgid(), *os.getgroups()}:
        raise HarnessError("Test account must be Standard, without administrator group membership")
    if home.is_relative_to(ROOT) or original.is_relative_to(ROOT):
        raise HarnessError("Unexpected home path")
    return name, home, original


def tree_manifest(app):
    """Hash files and preserve symlink text; reject escapes and special files."""
    app = Path(app).absolute()
    if not app.is_dir() or app.is_symlink() or app.resolve() != app:
        raise HarnessError("Game app must be a real directory")
    found = {}
    for base, dirs, files in os.walk(app, followlinks=False):
        for name in sorted(dirs + files):
            path = Path(base) / name
            relative = path.relative_to(app).as_posix()
            if path.is_symlink():
                if not path.resolve(strict=True).is_relative_to(app):
                    raise HarnessError("Game symlink escapes its app copy")
                found[relative] = {"link": os.readlink(path)}
            elif path.is_file():
                if path.stat().st_nlink != 1:
                    raise HarnessError("Game file is hard-linked outside the copy")
                found[relative] = {"sha256": digest(path), "mode": path.stat().st_mode & 0o7777}
            elif path.is_dir():
                found[relative] = {"directory": True}
            else:
                raise HarnessError("Game app contains an unsupported file type")
    return found


def verified_app(app):
    app = Path(app).absolute()
    if not app.is_dir() or app.is_symlink() or app.resolve() != app:
        raise HarnessError("Game app must be a real directory")
    for name in (ASSEMBLY, EXECUTABLE, "Contents/Resources/release_info.json"):
        path = app / name
        if path.is_symlink() or not path.is_file() or not path.resolve(strict=True).is_relative_to(app):
            raise HarnessError("Game critical file escapes the app")
    release = json.loads((app / "Contents/Resources/release_info.json").read_text())
    if release.get("version") != VERSION or release.get("commit") != COMMIT or digest(app / ASSEMBLY) != ASSEMBLY_HASH:
        raise HarnessError("Unsupported game build")
    result = subprocess.run(["/usr/bin/codesign", "--verify", "--deep", "--strict", str(app)],
                            capture_output=True, text=True)
    if result.returncode:
        raise HarnessError("Game signature verification failed: " + result.stderr[:500])
    return tree_manifest(app)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def prepare(source, session, original_home, test_user):
    name, home, original = test_identity(test_user, original_home)
    source = private_path(source, home)
    session = private_path(session, home)
    if source == session or session.is_relative_to(source) or source.is_relative_to(session) or session.is_relative_to(ROOT):
        raise HarnessError("Source and new session must be separate")
    if session.exists():
        raise HarnessError("Game session must be new")
    files = verified_app(source)
    session.mkdir(mode=0o700)
    app = session / "SlayTheSpire2.app"
    shutil.copytree(source, app, symlinks=True)
    if verified_app(app) != files:
        raise HarnessError("Game copy differs from source")
    result = {"schema": 1, "game_version": VERSION, "commit": COMMIT,
              "test_user": name, "test_uid": os.getuid(), "test_home": str(home),
              "original_home": str(original), "source_app": str(source),
              "files": files, "game_modified": False, "game_signed": False}
    write_json(session / "manifest.json", result)
    return {"session": str(session), "file_count": len(files), "game_modified": False}


def running_conflicts():
    output = subprocess.run(["/bin/ps", "-axo", "pid=,pgid=,uid=,command="], capture_output=True, text=True, check=True).stdout
    blocked = []
    for line in output.splitlines():
        fields = line.strip().split(None, 3)
        if len(fields) != 4:
            raise HarnessError("Cannot parse process inventory")
        command = fields[3]
        if ("/Steam.app/Contents/" in command or "steam_osx" in command
                or "steamwebhelper" in command or "/SlayTheSpire2.app/Contents/MacOS/" in command
                or "/SlayTheSpire2.app/Contents/MacOS/Slay the Spire 2" in command):
            blocked.append(line.strip())
    return blocked


def supervised_game(line, process, app):
    fields = line.split(None, 3)
    if len(fields) != 4:
        return False
    pid, group, uid, command = fields
    if int(pid) == process.pid:
        return True
    executable = str(app / EXECUTABLE)
    return (int(group) == process.pid and int(uid) == os.getuid()
            and (command == executable or command.startswith(executable + " ")))


def game_policy(session, home, original):
    quoted = lambda path: json.dumps(str(path))
    return "\n".join([
        "(version 1)", "(allow default)", "(deny network*)", "(deny file-write*)",
        f"(deny file-read* file-write* (subpath {quoted(original)}))",
        f"(allow file-read* file-write* (subpath {quoted(home)}))",
        f"(allow file-read* file-write* (subpath {quoted(session)}))",
        '(allow file-write* (literal "/dev/null"))',
        '(deny mach-lookup (global-name "com.apple.securityd"))', "",
    ])


def launch(session, seconds):
    if not 1 <= seconds <= 60:
        raise HarnessError("Game launch limit is 1–60 seconds")
    session = Path(session).absolute()
    # Refuse a redirected manifest before opening it, even on a first launch.
    if session.is_symlink() or session.resolve() != session or (session / "manifest.json").is_symlink():
        raise HarnessError("Game session or manifest is redirected")
    manifest = json.loads((session / "manifest.json").read_text())
    name, home, original = test_identity(manifest["test_user"], manifest["original_home"])
    private_path(session, home)
    if session.stat().st_uid != os.getuid() or session.stat().st_mode & 0o077:
        raise HarnessError("Game session must be private and owned by the test user")
    if (manifest["schema"] != 1 or manifest["test_uid"] != os.getuid()
            or manifest["test_home"] != str(home) or name != manifest["test_user"]):
        raise HarnessError("Game session belongs to a different test identity")
    app = session / "SlayTheSpire2.app"
    if verified_app(app) != manifest["files"]:
        raise HarnessError("Prepared game copy changed")
    if running_conflicts():
        raise HarnessError("Close running Steam and STS2 processes before the isolated probe")
    attempt = Path(tempfile.mkdtemp(prefix="game-attempt-", dir=session))
    (attempt / "temp").mkdir(mode=0o700)
    policy = attempt / "offline.sb"
    policy.write_text(game_policy(session, home, original))
    command = ["/usr/bin/sandbox-exec", "-f", str(policy), str(app / EXECUTABLE),
               "--windowed", "--always-on-top", "--resolution", "1280x720",
               "--position", "80,80", "--force-steam=off", "--nomods"]
    environment = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "LANG": "en_US.UTF-8",
                   "TMPDIR": str(attempt / "temp")}
    report = {"schema": 1, "attempt": str(attempt), "test_uid": os.getuid(),
              "game_app": str(app), "expected_executable": str(app / EXECUTABLE),
              "seconds_limit": seconds, "steam_requested": False,
              "result": "ATTEMPTED", "isolation_verified": False}
    write_json(attempt / "report.json", report)
    with (attempt / "stdout.log").open("xb") as output:
        process = subprocess.Popen(command, cwd=session, env=environment, stdout=output,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        report["supervisor_pid"] = process.pid
        deadline = time.monotonic() + seconds
        try:
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    report["time_limit_reached"] = True
                    break
                try:
                    report["exit_code"] = process.wait(timeout=min(1, remaining))
                    break
                except subprocess.TimeoutExpired:
                    # The supervised game may appear in this inventory; reject all others.
                    conflicts = running_conflicts()
                    others = [line for line in conflicts if not supervised_game(line, process, app)]
                    for line in conflicts:
                        if supervised_game(line, process, app):
                            pid, _, uid, _ = line.split(None, 3)
                            if int(pid) != process.pid:
                                report["observed_game_pid"] = int(pid)
                                report["observed_game_uid"] = int(uid)
                                report["observed_executable"] = str(app / EXECUTABLE)
                    if others:
                        report["unexpected_process"] = True
                        break
        except (OSError, subprocess.SubprocessError) as error:
            report["monitor_error"] = str(error)[:500]
            raise
        finally:
            stop_probe(process)
            write_json(attempt / "report.json", report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("source", type=Path)
    prep.add_argument("session", type=Path)
    prep.add_argument("--original-home", type=Path, required=True)
    prep.add_argument("--test-user", required=True)
    run = sub.add_parser("launch")
    run.add_argument("session", type=Path)
    run.add_argument("--seconds", type=int, default=60)
    args = parser.parse_args(argv)
    try:
        result = (prepare(args.source, args.session, args.original_home, args.test_user)
                  if args.command == "prepare" else launch(args.session, args.seconds))
        print(json.dumps(result, indent=2))
        return 1 if result.get("unexpected_process") or result.get("exit_code", 0) not in (None, 0) else 0
    except (HarnessError, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print("Isolated game probe stopped: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
