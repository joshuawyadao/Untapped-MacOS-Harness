"""Reviewed game update boundaries, exercised with private synthetic records only."""
import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from harness import game_debug, game_update, main_companion
from harness import main_launcher as launcher, progress_backup
from harness.asar import HarnessError, sha256


class GameUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="sts2-game-update-test-")
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name).resolve()
        self.home.chmod(0o700)
        self.root = self.home / launcher.WORKSPACE_RELATIVE
        self.root.mkdir(parents=True, mode=0o700)
        self.root.chmod(0o700)
        for name in ("game", "companion", "backups", "runs", "preferences"):
            (self.root / name).mkdir(mode=0o700)
        self.binding = {
            "schema": 1, "uid": os.getuid(), "home": str(self.home),
            "source_tree_sha256": game_debug.ORIGINAL_TREE_SHA256,
            "steam_id": "12345678901234567", "profile": 1,
            "companion_asar_sha256": "synthetic-companion",
        }
        self.write("main-launch.json", self.binding)
        self.write("main-proposal.json", {"synthetic": "proposal"})
        self.write("activation.json", {"schema": 1, "copied_apps_signed": True,
                   "proposal_sha256": sha256((self.root / "main-proposal.json").read_bytes())})
        self.write("game/debug-game.json", {"synthetic": "old-baseline"})
        self.write("game/debug-game-signing.json", {"synthetic": "old-signature"})
        self.write("companion/manifest.json", {"main_steam_guard_version": 1,
                   "patched_asar_sha256": "synthetic-companion"})
        self.write("preferences/selected.json", {"character": "Silent", "tier": "selected"})
        self.source = self.home / "synthetic-native-source"

    def write(self, name, value):
        path = self.root / name
        if path.exists() or path.is_symlink():
            path.unlink()
        launcher._write(path, value)

    def publish_synthetic_selection(self):
        selected = self.root / game_update.DIRECTORY
        selected.mkdir(mode=0o700)
        self.write(f"{game_update.DIRECTORY}/{game_debug.BASE}", {"synthetic": "new-baseline"})
        self.write(f"{game_update.DIRECTORY}/{game_debug.RECEIPT}", {"synthetic": "new-signature"})
        self.write(game_update.RECEIPT, {
            "schema": 1, "approved": True, "game_version": game_update.BUILD.version,
            "commit": game_update.BUILD.commit,
            "source_tree_sha256": game_update.BUILD.tree_sha256,
            "lineage": game_update._lineage(self.root),
            "signed_receipt_sha256": game_update._metadata_hash(selected / game_debug.RECEIPT),
            "baseline_sha256": game_update._metadata_hash(selected / game_debug.BASE),
        })
        return selected

    def test_selector_requires_complete_fixed_path_publication_and_verifies_selected_copy(self):
        self.assertEqual(game_update.selected_game(self.root), (self.root / "game", None))
        selected = self.root / game_update.DIRECTORY
        selected.mkdir(mode=0o700)
        with self.assertRaisesRegex(HarnessError, "Incomplete"):
            game_update.selected_game(self.root)
        selected.rmdir()
        self.write(game_update.RECEIPT, {"schema": 1})
        with self.assertRaisesRegex(HarnessError, "Incomplete"):
            game_update.selected_game(self.root)
        (self.root / game_update.RECEIPT).unlink()
        selected = self.publish_synthetic_selection()
        with patch.object(game_update.game_debug, "verify") as verify:
            self.assertEqual(game_update.verify_selected_game(self.root), (selected, game_update.BUILD))
        verify.assert_called_once_with(selected, build=game_update.BUILD)

    def test_selector_rejects_mutated_lineage_receipts_and_symlinks(self):
        selected = self.publish_synthetic_selection()
        cases = [
            ("uid", "main-launch.json", {**self.binding, "uid": os.getuid() + 1}),
            ("profile", "main-launch.json", {**self.binding, "profile": 2}),
            ("steam", "main-launch.json", {**self.binding, "steam_id": "other"}),
            ("baseline", f"{game_update.DIRECTORY}/{game_debug.BASE}", {"synthetic": "changed"}),
            ("signed receipt", f"{game_update.DIRECTORY}/{game_debug.RECEIPT}", {"synthetic": "changed"}),
            ("old signed receipt", "game/debug-game-signing.json", {"synthetic": "changed"}),
        ]
        for label, name, mutated in cases:
            with self.subTest(label=label):
                path = self.root / name
                original = path.read_bytes()
                self.write(name, mutated)
                with self.assertRaises(HarnessError):
                    game_update.selected_game(self.root)
                path.write_bytes(original)
                path.chmod(0o600)
        receipt = self.root / game_update.RECEIPT
        original = receipt.read_bytes()
        for value in ({**json.loads(original), "approved": False},
                      {**json.loads(original), "schema": True}):
            self.write(game_update.RECEIPT, value)
            with self.assertRaises(HarnessError):
                game_update.selected_game(self.root)
        receipt.write_bytes(original)
        receipt.chmod(0o600)
        receipt.unlink()
        receipt.symlink_to(selected / game_debug.BASE)
        with self.assertRaises((HarnessError, OSError)):
            game_update.selected_game(self.root)

    def test_real_prepared_selects_new_build_but_legacy_selection_rejects_changed_source(self):
        def source(_home, *, build=None):
            if build is None:
                raise launcher.LauncherError("SOURCE_CHANGED")
            self.assertIs(build, game_update.BUILD)
            return self.source

        with patch.object(launcher, "account", return_value=(os.getuid(), self.home)), \
             patch.object(launcher, "_source", side_effect=source) as checked_source, \
             patch.object(launcher, "_progress", return_value=(self.binding["steam_id"], 1)), \
             patch.object(launcher.controlled, "proposal", return_value={}):
            with self.assertRaises(launcher.LauncherError) as error:
                launcher._prepared()
            self.assertEqual(error.exception.code, "SOURCE_CHANGED")
            checked_source.reset_mock()
            self.publish_synthetic_selection()
            self.assertEqual(launcher._prepared(), (self.root, self.home, self.binding))
            checked_source.assert_called_once_with(self.home, build=game_update.BUILD)
            with patch.object(launcher, "_progress", return_value=("other-steam-id", 1)):
                with self.assertRaises(launcher.LauncherError):
                    launcher._prepared()
            with patch.object(launcher, "_progress", return_value=(self.binding["steam_id"], 2)):
                with self.assertRaises(launcher.LauncherError):
                    launcher._prepared()

    def install_patches(self, *, sign_error=None):
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(launcher, "account", return_value=(os.getuid(), self.home)))
        stack.enter_context(patch.object(launcher, "_closed"))
        stack.enter_context(patch.object(launcher, "_progress", return_value=(self.binding["steam_id"], 1)))
        source = stack.enter_context(patch.object(launcher, "_source", return_value=self.source))
        prepare = stack.enter_context(patch.object(game_update.game_debug, "prepare"))
        verify = stack.enter_context(patch.object(game_update.game_debug, "verify"))
        sign = stack.enter_context(patch.object(game_update.game_debug, "sign"))

        def fake_prepare(_source, session, *, build):
            self.assertIs(build, game_update.BUILD)
            session.mkdir(mode=0o700)
            launcher._write(session / game_debug.BASE, {"synthetic": "new-baseline"})
            (session / game_debug.APP).mkdir(mode=0o700)

        def fake_sign(session, *, approved, build):
            self.assertTrue(approved)
            self.assertIs(build, game_update.BUILD)
            if sign_error:
                raise HarnessError(sign_error)
            launcher._write(session / game_debug.RECEIPT, {"synthetic": "new-signature"})

        prepare.side_effect = fake_prepare
        sign.side_effect = fake_sign
        return source, prepare, sign, verify

    def test_install_is_atomic_on_approval_and_signing_failure(self):
        original = {name: (self.root / name).read_bytes() for name in game_update.BASE_RECORDS
                    if (self.root / name).is_file()}
        with patch.object(game_update.game_debug, "prepare") as prepare:
            with self.assertRaises(HarnessError):
                game_update.install_main(approved=False)
            prepare.assert_not_called()
        _, _, _, verify = self.install_patches(sign_error="synthetic signing failure")
        with self.assertRaisesRegex(HarnessError, "synthetic signing failure"):
            game_update.install_main(approved=True)
        self.assertFalse((self.root / game_update.DIRECTORY).exists())
        self.assertFalse((self.root / game_update.RECEIPT).exists())
        self.assertEqual(original, {name: (self.root / name).read_bytes() for name in original})
        self.assertTrue(verify.called)

    def test_install_stops_on_account_progress_mismatch_before_copy_or_signing(self):
        _, prepare, sign, _ = self.install_patches()
        with patch.object(launcher, "_progress", return_value=("other-steam-id", 1)):
            with self.assertRaisesRegex(HarnessError, "Steam/profile binding changed"):
                game_update.install_main(approved=True)
        with patch.object(launcher, "_progress", return_value=(self.binding["steam_id"], 2)):
            with self.assertRaisesRegex(HarnessError, "Steam/profile binding changed"):
                game_update.install_main(approved=True)
        prepare.assert_not_called()
        sign.assert_not_called()
        self.assertFalse((self.root / game_update.RECEIPT).exists())
        self.assertFalse((self.root / game_update.DIRECTORY).exists())

    def test_install_publishes_only_new_copy_and_is_idempotent(self):
        retained = {name: (self.root / name).read_bytes() for name in
                    (*game_update.BASE_RECORDS, "companion/manifest.json", "preferences/selected.json")}
        source, prepare, sign, verify = self.install_patches()
        result = game_update.install_main(approved=True)
        self.assertTrue(result["game_update_installed"])
        self.assertFalse(result["already_installed"])
        self.assertEqual(game_update.selected_game(self.root),
                         (self.root / game_update.DIRECTORY, game_update.BUILD))
        self.assertEqual(retained, {name: (self.root / name).read_bytes() for name in retained})
        self.assertEqual((self.root / game_update.RECEIPT).stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.root / game_update.DIRECTORY).stat().st_mode & 0o777, 0o700)
        original_receipt = (self.root / game_update.RECEIPT).read_bytes()
        again = game_update.install_main(approved=True)
        self.assertTrue(again["already_installed"])
        self.assertEqual((self.root / game_update.RECEIPT).read_bytes(), original_receipt)
        self.assertEqual(retained, {name: (self.root / name).read_bytes() for name in retained})
        prepare.assert_called_once()
        sign.assert_called_once()
        self.assertGreaterEqual(verify.call_count, 3)
        self.assertTrue(all(call.kwargs.get("build") is game_update.BUILD for call in source.call_args_list))

    def test_start_launches_selected_copy_and_stops_if_selection_changes_during_confirmation(self):
        selected = self.publish_synthetic_selection()
        (selected / game_debug.APP).mkdir(mode=0o700)
        process = Mock(pid=2468)
        process.poll.return_value = None
        launched = []
        def run(selection):
            with patch.object(launcher, "_prepared", return_value=(self.root, self.home, self.binding)), \
                 patch.object(launcher, "_source", return_value=self.source) as source, \
                 patch.object(game_update, "verify_selected_game", side_effect=selection), \
                 patch.object(launcher, "_closed"), \
                 patch.object(launcher, "_steam_ready"), \
                 patch.object(launcher.cli, "_validate_launch_copy"), \
                 patch.object(launcher.live_inventory, "prepare", return_value=contextlib.nullcontext(None)), \
                 patch.object(launcher.subprocess, "Popen", return_value=process) as popen, \
                 patch.object(launcher, "_wait_for_steam", return_value=2468), \
                 patch.object(main_companion, "run", return_value={"synthetic": True}), \
                 patch.object(progress_backup, "create_backup", return_value={"verified": True}), \
                 patch.object(progress_backup, "verify_backup"), \
                 patch.object(progress_backup, "assert_source_unchanged"), \
                 patch("harness.fullscreen_update.selected_session", return_value=self.root / "companion"), \
                 contextlib.redirect_stdout(io.StringIO()):
                launched.append(popen)
                result = launcher.start(approved=True, cloud_confirmed=True, account_confirmed=True,
                                        confirm_steam=lambda: None, seconds=7200)
            return result, popen, source

        result, popen, source = run([(selected, game_update.BUILD)] * 3)
        self.assertTrue(result["game_left_running"])
        self.assertEqual(popen.call_args.args[0][0], str(selected / game_debug.APP / launcher.game_launch.EXECUTABLE))
        self.assertTrue(all(call.kwargs.get("build") is game_update.BUILD for call in source.call_args_list))
        with self.assertRaises(launcher.LauncherError) as error:
            run([(selected, game_update.BUILD), (self.root / "game", None)])
        self.assertEqual(error.exception.code, "PREPARATION_INVALID")
        launched[-1].assert_not_called()


if __name__ == "__main__":
    unittest.main()
