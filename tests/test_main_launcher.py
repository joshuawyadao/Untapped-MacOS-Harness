"""Copied-game orchestration is exercised with synthetic data and processes only."""
import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from harness import main_companion, main_launcher as launcher, progress_backup
from harness.asar import HarnessError, sha256


class MainLauncherTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name).resolve()
        self.root = self.home / "workspace"
        self.root.mkdir(mode=0o700)
        for name in ("backups", "runs", "preferences"):
            (self.root / name).mkdir(mode=0o700)
        self.binding = {"steam_id": "12345678901234567", "profile": 1}
        launcher._write(self.root / "main-proposal.json", {"proposal_only": True})
        launcher._write(self.root / "activation.json", {"schema": 1, "copied_apps_signed": True,
            "proposal_sha256": sha256((self.root / "main-proposal.json").read_bytes())})

    def patches(self, *, changed=False, startup_failed=False):
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        order = []
        stack.enter_context(patch.object(launcher, "_prepared", return_value=(self.root, self.home, self.binding)))
        stack.enter_context(patch.object(launcher, "_source", side_effect=lambda *a: order.append("source")))
        stack.enter_context(patch.object(launcher.game_debug, "verify"))
        stack.enter_context(patch.object(launcher.cli, "_validate_launch_copy"))
        stack.enter_context(patch.object(launcher, "_closed", side_effect=lambda: order.append("closed")))
        stack.enter_context(patch.object(launcher, "_steam_ready", side_effect=lambda: order.append("steam")))
        stack.enter_context(patch.object(progress_backup, "create_backup", side_effect=lambda *a: order.append("backup") or {"files": 2, "bytes": 10, "verified": True}))
        stack.enter_context(patch.object(progress_backup, "verify_backup", side_effect=lambda *a: order.append("verify")))
        def unchanged(*args):
            order.append("unchanged")
            if changed:
                raise HarnessError("private-path")
        stack.enter_context(patch.object(progress_backup, "assert_source_unchanged", side_effect=unchanged))
        process = Mock(pid=2468)
        process.poll.return_value = None
        popen = stack.enter_context(patch.object(launcher.subprocess, "Popen", side_effect=lambda *a, **kw: order.append("launch") or process))
        waiter = stack.enter_context(patch.object(launcher, "_wait_for_steam",
                        side_effect=launcher.LauncherError("STEAM_STARTUP_FAILED") if startup_failed else None,
                        return_value=2468))
        companion = stack.enter_context(patch.object(main_companion, "run", return_value={"account_verified": True}))
        return order, process, popen, waiter, companion

    def start(self, confirm=None):
        return launcher.start(approved=True, cloud_confirmed=True, account_confirmed=True,
                              confirm_steam=confirm or (lambda: None), seconds=7200)

    def test_no_activation_or_live_approvals_never_reaches_user_data(self):
        with patch.object(launcher, "_prepared") as prepared:
            with self.assertRaisesRegex(launcher.LauncherError, "confirmations"):
                launcher.start()
            prepared.assert_not_called()
        with patch.object(launcher, "_prepared") as prepared:
            with self.assertRaises(launcher.LauncherError):
                launcher.activate(approved=False)
            prepared.assert_not_called()

    def test_main_proposal_discloses_long_session_without_test_auth_cutoff(self):
        with patch.object(launcher.controlled, "proposal", return_value={"maximum_seconds": 300,
                       "post_auth_maximum_seconds": 45, "gateway_sha256": "fixed"}):
            review = launcher._gateway_review(self.root)
        self.assertEqual(review["default_seconds"], 14400)
        self.assertEqual(review["maximum_seconds"], 28800)
        self.assertIsNone(review["post_auth_maximum_seconds"])
        self.assertFalse(review["authentication_shortens_session"])
        self.assertEqual(review["gateway_sha256"], "fixed")

    def test_missing_activation_stops_before_backup_or_game(self):
        (self.root / "activation.json").unlink()
        with patch.object(launcher, "_prepared", return_value=(self.root, self.home, self.binding)), \
             patch.object(progress_backup, "create_backup") as backup:
            with self.assertRaises(launcher.LauncherError) as error:
                self.start()
        self.assertEqual(error.exception.code, "ACTIVATION_REQUIRED")
        backup.assert_not_called()

    def test_backup_confirm_steam_and_recheck_precede_launch(self):
        order, process, popen, _, companion = self.patches()
        with contextlib.redirect_stdout(io.StringIO()) as output:
            result = self.start(lambda: order.append("owner"))
        self.assertEqual(order, ["closed", "backup", "verify", "owner", "steam", "source", "unchanged", "source", "launch"])
        command = popen.call_args.args[0]
        options = popen.call_args.kwargs
        self.assertIn("--force-steam=on", command)
        self.assertIn("--nomods", command)
        self.assertNotIn("sandbox-exec", command)
        self.assertEqual(options["env"]["SteamAppId"], launcher.APP_ID)
        self.assertNotIn("NODE_OPTIONS", options["env"])
        self.assertEqual((options["cwd"] / "steam_appid.txt").read_text().strip(), launcher.APP_ID)
        self.assertEqual(companion.call_args.kwargs["expected_steam_id"], self.binding["steam_id"])
        self.assertEqual(companion.call_args.kwargs["expected_profile"], 1)
        self.assertTrue(result["game_left_running"])
        self.assertNotIn(self.binding["steam_id"], json.dumps(result) + output.getvalue())
        process.kill.assert_not_called()
        process.terminate.assert_not_called()

    def test_changed_progress_never_launches_or_restores(self):
        _, process, popen, _, companion = self.patches(changed=True)
        with self.assertRaises(launcher.LauncherError) as error:
            self.start()
        self.assertEqual(error.exception.code, "PROGRESS_CHANGED")
        popen.assert_not_called()
        companion.assert_not_called()
        process.kill.assert_not_called()

    def test_steam_update_during_owner_confirmation_never_launches(self):
        _, _, popen, _, companion = self.patches()
        with patch.object(launcher, "_source", side_effect=launcher.LauncherError("SOURCE_CHANGED")):
            with self.assertRaises(launcher.LauncherError) as error:
                self.start()
        self.assertEqual(error.exception.code, "SOURCE_CHANGED")
        popen.assert_not_called()
        companion.assert_not_called()

    def test_startup_failure_never_attaches_or_kills_game(self):
        _, process, _, _, companion = self.patches(startup_failed=True)
        with contextlib.redirect_stdout(io.StringIO()) as output, self.assertRaises(launcher.LauncherError):
            self.start()
        companion.assert_not_called()
        process.kill.assert_not_called()
        process.terminate.assert_not_called()
        self.assertIn("Quit it normally", output.getvalue())

    def test_steam_markers_are_boolean_evidence_not_an_account_export(self):
        log = self.root / "game.log"
        log.write_text("private-user-and-token\n" + launcher.STEAM_OK + "\n" + launcher.CLOUD_STORE + "True, app: True")
        result = launcher._steam_status(log)
        self.assertEqual(result, {"initialized": True, "cloud_store_enabled_logged": True, "failed": False})
        log.write_text(launcher.STEAM_FAILURES[0])
        self.assertTrue(launcher._steam_status(log)["failed"])
        self.assertNotIn("private-user", json.dumps(result))

    def test_progress_selection_requires_a_single_private_namespace_and_real_profile(self):
        data = self.home / "data"
        for number in (0, 1):
            (data / "steam" / self.binding["steam_id"] / f"profile{number}").mkdir(parents=True)
        with self.assertRaises(launcher.LauncherError):
            launcher._progress(data)
        self.assertEqual(launcher._progress(data, 1), (self.binding["steam_id"], 1))
        (data / "steam" / "987" / "profile1").mkdir(parents=True)
        with self.assertRaises(launcher.LauncherError):
            launcher._progress(data, 1)

    def test_steam_and_target_process_guards_preserve_identity(self):
        with patch.object(launcher, "_inventory", return_value=[(1, os.getuid(), "/Steam.app/steam", True)]):
            with self.assertRaises(launcher.LauncherError):
                launcher._closed()
            launcher._steam_ready()
        expected = self.root / "copied-game"
        rows = [(5, os.getuid(), str(expected), False), (7, os.getuid(), "/Steam.app/steam", True)]
        with patch.object(launcher, "_inventory", return_value=rows), patch.object(launcher.os, "getpgid", return_value=5):
            self.assertEqual(launcher._target(expected, 5), 5)
            with self.assertRaises(launcher.LauncherError):
                launcher._target(expected, 9)

    def test_cli_errors_are_fixed_and_do_not_expose_private_exceptions(self):
        output = io.StringIO()
        with patch.object(launcher, "proposal", side_effect=OSError("private-path-secret")), contextlib.redirect_stderr(output):
            code = launcher.main(["proposal"])
        self.assertEqual(code, 2)
        self.assertIn("INSPECTION_FAILED", output.getvalue())
        self.assertNotIn("private-path-secret", output.getvalue())

    def test_cli_start_does_not_report_failure_as_success(self):
        args = ["start", "--approve-main-account-launch", "--confirm-cloud-synced", "--confirm-steam-account"]
        with patch.object(launcher.sys.stdin, "isatty", return_value=True), \
             patch.object(launcher, "start", return_value={"companion": {"failure_stage": "LAUNCH"}}), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(launcher.main(args), 1)


if __name__ == "__main__":
    unittest.main()
