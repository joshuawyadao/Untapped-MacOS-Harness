"""Run one bounded companion probe against the isolated STS2 test account."""

import argparse
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

from . import cli, game_launch
from .asar import HarnessError


def _steam_process(command):
    lower = command.lower()
    return ("/steam.app/contents/" in lower
            or Path(lower).name in {"steam_osx", "steamwebhelper", "steam"})


def _candidates(output):
    for line in output.splitlines():
        fields = line.strip().split(None, 2)
        if not fields:
            continue
        if len(fields) != 3:
            if "Slay the Spire 2" in line or "steam" in line.lower():
                raise HarnessError("Cannot parse a game or Steam process")
            continue
        pid_text, uid_text, command = fields
        steam = _steam_process(command)
        game = Path(command).name == "Slay the Spire 2"
        if not (steam or game):
            continue
        if not pid_text.isdecimal() or not uid_text.isdecimal() or int(pid_text) <= 0:
            raise HarnessError("Cannot parse a game or Steam process")
        yield int(pid_text), int(uid_text), command, steam


def select_target(output, expected, uid):
    """Select the sole copied game from a complete `ps -axo pid=,uid=,comm=` listing."""
    expected = str(expected)
    found = []
    for pid, process_uid, command, steam in _candidates(output):
        if steam:
            raise HarnessError("Close Steam in every account before the probe")
        if process_uid != uid or command != expected:
            raise HarnessError("Running game belongs to another user or copy")
        found.append(pid)
    if len(found) != 1:
        raise HarnessError("Exactly one copied Slay the Spire 2 process is required")
    return found[0]


def _private_session(session, home):
    session = Path(session).absolute()
    if session.is_symlink() or session.resolve(strict=True) != session:
        raise HarnessError("Companion session is redirected")
    if session.is_relative_to(home):
        session = game_launch.private_path(session, home)
    else:
        prefix = f"uc-sts2-{os.getuid()}-"
        if session.parent != Path("/private/tmp") or not session.name.startswith(prefix) or len(session.name) <= len(prefix):
            raise HarnessError("Companion session must be inside the test home or assigned private tmp namespace")
    if not session.is_dir():
        raise HarnessError("Companion session does not exist")
    info = session.stat()
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise HarnessError("Companion session must be owned by the test user and mode 0700")
    return session


def _process_inventory():
    return subprocess.run(["/bin/ps", "-axo", "pid=,uid=,comm="],
                          capture_output=True, text=True, check=True, timeout=2).stdout


def run(session):
    _, home, _ = game_launch.test_identity("sts2test", game_launch.PROTECTED_HOME)
    session = _private_session(session, home)

    expected = home / "UntappedSTS2GameSession" / "SlayTheSpire2.app" / game_launch.EXECUTABLE
    expected = game_launch.private_path(expected, home)
    if not expected.is_file() or expected.is_symlink():
        raise HarnessError("Copied game executable is missing or redirected")

    pid = select_target(_process_inventory(), expected, os.getuid())
    return cli.launch_outer(session, 45, approved=True, target_pid=pid, target_game=expected)


def run_startup(session):
    """Observe companion startup while Steam and every STS2 copy are absent."""
    _, home, _ = game_launch.test_identity("sts2test", game_launch.PROTECTED_HOME)
    session = _private_session(session, home)
    for _, _, _, steam in _candidates(_process_inventory()):
        if steam:
            raise HarnessError("Close Steam in every account before the probe")
        raise HarnessError("Close every Slay the Spire 2 process before the startup probe")
    return cli.launch_outer(session, 45, approved=True)


def main(argv=None):
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("companion_session", type=Path)
    parser.add_argument("--startup-only", action="store_true", help="Probe startup with no game or Steam running")
    args = parser.parse_args(argv)
    try:
        report = run_startup(args.companion_session) if args.startup_only else run(args.companion_session)
        print(json.dumps(report, indent=2))
        launch_exit = (report.get("launch") or {}).get("exit_code", 0)
        failed = (report.get("startup") != "ELECTRON_READY"
                  or bool(report.get("startup_blockers")) or launch_exit not in (None, 0))
        return 1 if failed else 0
    except (HarnessError, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f"Harness stopped: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
