"""Synthetic checks for the approved, fresh-profile outer sandbox probe."""
import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from harness import cli
from harness.asar import HarnessError


class OuterLaunchTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.session = Path(self.temporary.name).resolve()
        self.app = self.session / "Companion.app"
        self.app.mkdir()
        self.manifest = {"schema": 1, "patched_asar_sha256": "synthetic"}
        (self.session / "signing.json").write_text("{}")
        profile = self.session / "profile"
        profile.mkdir()
        (profile / "acceptedTOS").write_text("private old setting")

    def test_no_approval_stops_before_filesystem_or_process_access(self):
        with mock.patch.object(cli, "_validate_launch_copy") as validate, \
                mock.patch.object(cli.subprocess, "Popen") as spawn, \
                mock.patch.object(cli.tempfile, "mkdtemp") as make_attempt:
            with self.assertRaisesRegex(HarnessError, "Explicit owner approval"):
                cli.launch_outer(Path("/does/not/exist"), 10)
        validate.assert_not_called()
        spawn.assert_not_called()
        make_attempt.assert_not_called()

    def test_signed_receipt_is_required_before_creating_attempt(self):
        (self.session / "signing.json").unlink()
        with mock.patch.object(cli, "_validate_launch_copy", return_value=(self.session, self.manifest, self.app)), \
                mock.patch.object(cli.tempfile, "mkdtemp") as make_attempt, \
                mock.patch.object(cli.subprocess, "Popen") as spawn:
            with self.assertRaisesRegex(HarnessError, "verified signed disposable copy"):
                cli.launch_outer(self.session, 10, approved=True)
        make_attempt.assert_not_called()
        spawn.assert_not_called()

    def test_validation_failure_prevents_attempt_creation_and_spawn(self):
        with mock.patch.object(cli, "_validate_launch_copy", side_effect=HarnessError("changed archive")), \
                mock.patch.object(cli.tempfile, "mkdtemp") as make_attempt, \
                mock.patch.object(cli.subprocess, "Popen") as spawn:
            with self.assertRaisesRegex(HarnessError, "changed archive"):
                cli.launch_outer(self.session, 10, approved=True)
        make_attempt.assert_not_called()
        spawn.assert_not_called()

    def test_fresh_profile_command_policy_and_outputs_are_isolated(self):
        process = mock.Mock(pid=43210)
        process.wait.return_value = 0
        commands = []

        def spawn(command, **options):
            commands.append((command, options))
            self.assertTrue(options["start_new_session"])
            self.assertEqual(options["cwd"], self.session)
            self.assertTrue(Path(options["env"]["UC_TEST_SANDBOX_DIR"]).is_dir())
            return process

        with mock.patch.object(cli, "_validate_launch_copy", return_value=(self.session, self.manifest, self.app)), \
                mock.patch.object(cli.subprocess, "Popen", side_effect=spawn), \
                mock.patch.object(cli, "stop_probe") as stop:
            first = cli.launch_outer(self.session, 7, approved=True)
            second = cli.launch_outer(self.session, 7, approved=True)
        self.assertEqual(stop.call_count, 2)
        self.assertEqual(len(commands), 2)
        self.assertNotEqual(first["attempt_dir"], second["attempt_dir"])
        for result, (command, options) in zip((first, second), commands):
            attempt = Path(result["attempt_dir"])
            profile = attempt / "profile"
            self.assertEqual(command[0:2], ["/usr/bin/sandbox-exec", "-f"])
            self.assertEqual(command[2], str(attempt / "offline.sb"))
            self.assertEqual(command[3], str(self.app / "Contents/MacOS/Untapped.gg Companion"))
            self.assertEqual(command[4:], ["--user-data-dir=" + str(profile), "--no-sandbox"])
            self.assertEqual(options["env"]["UC_TEST_SANDBOX_DIR"], str(profile))
            self.assertEqual(options["env"]["TMPDIR"], str(profile / "temp"))
            self.assertEqual(options["env"]["MAC_CHROMIUM_TMPDIR"], str(self.session / "t"))
            self.assertEqual(options["env"]["UC_SKIP_UPDATE_CHECKS"], "1")
            self.assertFalse((profile / "acceptedTOS").exists())
            self.assertTrue((self.session / "t").is_dir())
            policy = (attempt / "offline.sb").read_text()
            self.assertIn("(deny network*)", policy)
            self.assertIn("(deny file-write*)", policy)
            self.assertIn("(allow network*", policy)
            self.assertIn(str(self.session), policy)
            self.assertEqual(json.loads((attempt / "launch.json").read_text())["outer_sandbox_retained"], True)
            self.assertEqual(json.loads((attempt / "manifest.json").read_text())["profile_is_fresh"], True)
            self.assertEqual(json.loads((attempt / "report.json").read_text())["attempt_dir"], str(attempt))
            self.assertEqual(result["companion_initialization"], "NOT_OBSERVED")

    def test_timeout_still_stops_probe_and_records_it(self):
        process = mock.Mock(pid=43211)
        process.wait.side_effect = subprocess.TimeoutExpired(cmd="synthetic", timeout=1)
        with mock.patch.object(cli, "_validate_launch_copy", return_value=(self.session, self.manifest, self.app)), \
                mock.patch.object(cli.subprocess, "Popen", return_value=process), \
                mock.patch.object(cli, "stop_probe") as stop:
            result = cli.launch_outer(self.session, 1, approved=True)
        stop.assert_called_once_with(process)
        self.assertTrue(result["launch"]["time_limit_reached"])
        self.assertEqual(result["startup"], "NOT_OBSERVED")

    def test_cli_passes_explicit_outer_flag_and_reports_failure_without_evidence(self):
        fake = {"startup": "NOT_OBSERVED", "startup_blockers": [], "attempt_dir": "synthetic"}
        with mock.patch.object(cli, "launch_outer", return_value=fake) as launch, \
                contextlib.redirect_stdout(io.StringIO()):
            result = cli.main(["launch-outer", str(self.session), "--seconds", "8",
                               "--approve-outer-sandbox-only"])
        self.assertEqual(result, 1)
        launch.assert_called_once_with(self.session, 8, approved=True)
        with mock.patch.object(cli, "launch_outer", return_value=fake) as launch, \
                contextlib.redirect_stdout(io.StringIO()):
            cli.main(["launch-outer", str(self.session)])
        launch.assert_called_once_with(self.session, 45, approved=False)

    def test_cli_rejects_crash_after_ready_but_preserves_bounded_timeout_result(self):
        for command, function in (("launch", "launch"), ("launch-outer", "launch_outer")):
            for outcome, expected in (({"exit_code": -6}, 1), ({"exit_code": 0}, 0),
                                      ({"time_limit_reached": True}, 0)):
                fake = {"startup": "ELECTRON_READY", "startup_blockers": [], "launch": outcome}
                with self.subTest(command=command, outcome=outcome), \
                        mock.patch.object(cli, function, return_value=fake), \
                        contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(cli.main([command, str(self.session)]), expected)


if __name__ == "__main__":
    unittest.main()
