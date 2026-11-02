"""The isolated reward probe rejects ambiguous processes before launching."""

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from harness import reward_probe
from harness.asar import HarnessError


class TargetSelectionTests(unittest.TestCase):
    expected = Path("/Users/sts2test/Game with spaces/SlayTheSpire2.app/Contents/MacOS/Slay the Spire 2")
    uid = 502

    def test_selects_only_exact_copied_game(self):
        listing = f"  1 0 /sbin/launchd\n 345 {self.uid} {self.expected}\n"
        self.assertEqual(reward_probe.select_target(listing, self.expected, self.uid), 345)

    def test_rejects_wrong_user_path_duplicate_steam_or_missing(self):
        valid = f"345 {self.uid} {self.expected}\n"
        cases = [
            f"345 {self.uid + 1} {self.expected}\n",
            f"345 {self.uid} /another/Slay the Spire 2\n",
            valid + f"346 {self.uid} {self.expected}\n",
            valid + "99 501 /Applications/Steam.app/Contents/MacOS/steam_osx\n",
            "1 0 /sbin/launchd\n",
            f"not-a-pid {self.uid} {self.expected}\n",
            "345 Slay the Spire 2\n",
        ]
        for listing in cases:
            with self.subTest(listing=listing), self.assertRaises(HarnessError):
                reward_probe.select_target(listing, self.expected, self.uid)


class ProbeDispatchTests(unittest.TestCase):
    def test_only_guarded_forty_five_second_launch_is_dispatched(self):
        with tempfile.TemporaryDirectory() as root:
            home = Path(root).resolve()
            session = home / "companion"
            session.mkdir(mode=0o700)
            game = home / "UntappedSTS2GameSession" / "SlayTheSpire2.app" / "Contents" / "MacOS" / "Slay the Spire 2"
            game.parent.mkdir(parents=True)
            game.touch()
            listing = f"55 {os.getuid()} {game}\n"
            report = {"startup": "ELECTRON_READY", "startup_blockers": [], "launch": {"exit_code": 0}}
            with patch.object(reward_probe.game_launch, "test_identity", return_value=("sts2test", home, Path("/protected"))) as identity, patch.object(reward_probe.subprocess, "run", return_value=SimpleNamespace(stdout=listing)) as inventory, patch.object(reward_probe.cli, "launch_outer", return_value=report) as launch, redirect_stdout(io.StringIO()):
                self.assertEqual(reward_probe.main([str(session)]), 0)
            identity.assert_called_once_with("sts2test", reward_probe.game_launch.PROTECTED_HOME)
            inventory.assert_called_once_with(["/bin/ps", "-axo", "pid=,uid=,comm="], capture_output=True, text=True, check=True, timeout=2)
            launch.assert_called_once_with(session, 45, approved=True, target_pid=55, target_game=game)

    def test_startup_failure_returns_nonzero(self):
        for report in ({"startup": "NOT_OBSERVED", "startup_blockers": [], "launch": {}},
                       {"startup": "ELECTRON_READY", "startup_blockers": ["socket"], "launch": {}},
                       {"startup": "ELECTRON_READY", "startup_blockers": [], "launch": {"exit_code": 1}}):
            with self.subTest(report=report), patch.object(reward_probe, "run", return_value=report), redirect_stdout(io.StringIO()):
                self.assertEqual(reward_probe.main(["/unused"]), 1)

    def test_private_tmp_session_startup_only_dispatches_without_target(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory(prefix=f"uc-sts2-{os.getuid()}-", dir="/private/tmp") as tmp:
            home = Path(root).resolve()
            session = Path(tmp).resolve()
            report = {"startup": "ELECTRON_READY", "startup_blockers": [], "launch": {"exit_code": 0}}
            with patch.object(reward_probe.game_launch, "test_identity", return_value=("sts2test", home, Path("/protected"))), patch.object(reward_probe.subprocess, "run", return_value=SimpleNamespace(stdout="1 0 /sbin/launchd\n")) as inventory, patch.object(reward_probe.cli, "launch_outer", return_value=report) as launch, redirect_stdout(io.StringIO()):
                self.assertEqual(reward_probe.main([str(session), "--startup-only"]), 0)
            inventory.assert_called_once_with(["/bin/ps", "-axo", "pid=,uid=,comm="], capture_output=True, text=True, check=True, timeout=2)
            launch.assert_called_once_with(session, 45, approved=True)

    def test_startup_only_rejects_game_steam_and_malformed_candidates(self):
        with tempfile.TemporaryDirectory() as root:
            home = Path(root).resolve()
            session = home / "companion"
            session.mkdir(mode=0o700)
            cases = [
                "21 777 /other/Slay the Spire 2\n",
                "33 777 /Applications/Steam.app/Contents/MacOS/steam_osx\n",
                "bad 777 /other/Slay the Spire 2\n",
                "33 Steam.app/Contents/MacOS/steam_osx\n",
            ]
            for listing in cases:
                with self.subTest(listing=listing), patch.object(reward_probe.game_launch, "test_identity", return_value=("sts2test", home, Path("/protected"))), patch.object(reward_probe.subprocess, "run", return_value=SimpleNamespace(stdout=listing)), patch.object(reward_probe.cli, "launch_outer") as launch:
                    with self.assertRaises(HarnessError):
                        reward_probe.run_startup(session)
                    launch.assert_not_called()

    def test_tmp_namespace_and_private_mode_are_required(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory(dir="/private/tmp") as unrelated:
            home = Path(root).resolve()
            session = home / "companion"
            session.mkdir(mode=0o700)
            link = home / "redirected"
            link.symlink_to(session, target_is_directory=True)
            examples = [Path(unrelated), link, Path("/private/tmp") / f"uc-sts2-{os.getuid()}-", Path("/private/tmp") / f"uc-sts2-{os.getuid() + 1}-abc"]
            for path in examples:
                with self.subTest(path=path), self.assertRaises((HarnessError, OSError)):
                    reward_probe._private_session(path, home)
            session.chmod(0o750)
            with self.assertRaises(HarnessError):
                reward_probe._private_session(session, home)


if __name__ == "__main__":
    unittest.main()
