"""Synthetic game-copy and bounded-launch checks; no game executable runs."""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from harness.asar import HarnessError
from harness import game_launch as game


class GameLaunchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.home = self.root / "test-home"
        self.original = self.root / "original-home"
        self.home.mkdir()
        self.original.mkdir()
        self.source = self.home / "Source.app"
        self.session = self.home / "session"
        self.assembly = self.source / game.ASSEMBLY
        self.assembly.parent.mkdir(parents=True)
        self.assembly.write_bytes(b"synthetic assembly")
        exe = self.source / game.EXECUTABLE
        exe.parent.mkdir(parents=True)
        exe.write_bytes(b"synthetic executable")
        (self.source / "Contents/Resources/release_info.json").write_text(json.dumps({
            "version": game.VERSION, "commit": game.COMMIT,
        }))
        self.platform_patch = mock.patch.object(game.platform, "system", return_value="Darwin")
        self.uid_patch = mock.patch.object(game.os, "getuid", return_value=501)
        self.pwd_patch = mock.patch.object(game.pwd, "getpwuid", return_value=SimpleNamespace(pw_name="sts2test", pw_dir=str(self.home)))
        self.hash_patch = mock.patch.object(game, "ASSEMBLY_HASH", game.digest(self.assembly))
        self.protected_patch = mock.patch.object(game, "PROTECTED_HOME", self.original)
        self.groups_patch = mock.patch.object(game.os, "getgroups", return_value=[20])
        self.gid_patch = mock.patch.object(game.os, "getgid", return_value=20)
        self.admin_patch = mock.patch.object(game.grp, "getgrnam", return_value=SimpleNamespace(gr_gid=80))
        self.sign_patch = mock.patch.object(game.subprocess, "run", return_value=SimpleNamespace(returncode=0, stderr=""))
        for patcher in (self.platform_patch, self.uid_patch, self.pwd_patch, self.hash_patch,
                        self.protected_patch, self.groups_patch, self.gid_patch, self.admin_patch,
                        self.sign_patch):
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_prepare_preserves_exact_copy_and_rejects_change(self):
        result = game.prepare(self.source, self.session, self.original, "sts2test")
        self.assertFalse(result["game_modified"])
        manifest = json.loads((self.session / "manifest.json").read_text())
        self.assertEqual(manifest["files"], game.tree_manifest(self.session / "SlayTheSpire2.app"))
        (self.session / "SlayTheSpire2.app" / game.EXECUTABLE).write_bytes(b"changed")
        with self.assertRaisesRegex(HarnessError, "copy changed"):
            with mock.patch.object(game, "running_conflicts", return_value=[]):
                game.launch(self.session, 1)

    def test_prepare_refuses_normal_user_and_external_symlink(self):
        with self.assertRaisesRegex(HarnessError, "differ"):
            game.prepare(self.source, self.session, self.home, "sts2test")
        external = self.root / "outside"
        external.write_text("outside")
        (self.source / "escape").symlink_to(external)
        with self.assertRaisesRegex(HarnessError, "symlink escapes"):
            game.prepare(self.source, self.session, self.original, "sts2test")
        self.assertFalse(self.session.exists())

    def test_prepare_rejects_admin_group_and_false_original_home(self):
        with mock.patch.object(game.os, "getgroups", return_value=[20, 80]):
            with self.assertRaisesRegex(HarnessError, "Standard"):
                game.prepare(self.source, self.session, self.original, "sts2test")
        another = self.root / "other-home"
        another.mkdir()
        with self.assertRaisesRegex(HarnessError, "differ"):
            game.prepare(self.source, self.session, another, "sts2test")

    def test_launch_refuses_running_steam_before_spawn(self):
        game.prepare(self.source, self.session, self.original, "sts2test")
        with mock.patch.object(game, "running_conflicts", return_value=["42 /Applications/Steam.app/Contents/MacOS/steam_osx"]), \
                mock.patch.object(game.subprocess, "Popen") as spawn:
            with self.assertRaisesRegex(HarnessError, "Close running Steam"):
                game.launch(self.session, 1)
        spawn.assert_not_called()

    def test_launch_constructs_offline_command_and_cleans_up(self):
        game.prepare(self.source, self.session, self.original, "sts2test")
        process = mock.Mock(pid=1234)
        process.wait.side_effect = subprocess.TimeoutExpired("game", 1)
        with mock.patch.object(game, "running_conflicts", return_value=[]), \
                mock.patch.object(game.subprocess, "Popen", return_value=process) as spawn, \
                mock.patch.object(game, "stop_probe") as stop, \
                mock.patch.object(game.time, "monotonic", side_effect=[0, 0, 2]):
            report = game.launch(self.session, 1)
        self.assertTrue(report["time_limit_reached"])
        stop.assert_called_once_with(process)
        args, options = spawn.call_args
        self.assertEqual(args[0][-2:], ["--force-steam=off", "--nomods"])
        self.assertEqual(options["env"].keys(), {"PATH", "LANG", "TMPDIR"})
        self.assertTrue(options["start_new_session"])
        policy = next(self.session.glob("game-attempt-*/offline.sb")).read_text()
        self.assertIn("(deny network*)", policy)
        self.assertIn(str(self.original), policy)
        self.assertIn(str(self.home), policy)
        self.assertFalse(report["isolation_verified"])

    def test_monitor_error_still_stops_supervised_group(self):
        game.prepare(self.source, self.session, self.original, "sts2test")
        process = mock.Mock(pid=1234)
        process.wait.side_effect = subprocess.TimeoutExpired("game", 1)
        with mock.patch.object(game, "running_conflicts", side_effect=[[], OSError("ps unavailable")]), \
                mock.patch.object(game.subprocess, "Popen", return_value=process), \
                mock.patch.object(game, "stop_probe") as stop, \
                mock.patch.object(game.time, "monotonic", side_effect=[0, 0]):
            with self.assertRaisesRegex(OSError, "ps unavailable"):
                game.launch(self.session, 1)
        stop.assert_called_once_with(process)
        report = json.loads(next(self.session.glob("game-attempt-*/report.json")).read_text())
        self.assertEqual(report["monitor_error"], "ps unavailable")

    def test_monitor_allows_own_game_child_but_rejects_other_group(self):
        app = self.session / "SlayTheSpire2.app"
        process = mock.Mock(pid=1234)
        own = f"1235 1234 501 {app / game.EXECUTABLE} --nomods"
        other = f"1236 1236 501 {app / game.EXECUTABLE} --nomods"
        self.assertTrue(game.supervised_game(own, process, app))
        self.assertFalse(game.supervised_game(other, process, app))

    def test_launch_rejects_redirected_manifest_before_read(self):
        game.prepare(self.source, self.session, self.original, "sts2test")
        manifest = self.session / "manifest.json"
        outside = self.root / "outside-manifest.json"
        manifest.rename(outside)
        manifest.symlink_to(outside)
        with self.assertRaisesRegex(HarnessError, "redirected"):
            game.launch(self.session, 1)


if __name__ == "__main__":
    unittest.main()
