"""Offline update selection and preservation guards, without vendor data."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from harness import main_launcher, ui_update
from harness.asar import HarnessError


class UiUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.root.chmod(0o700)
        self.base = self.root / 'companion'
        self.base.mkdir(mode=0o700)
        self.new = self.root / ui_update.UPDATE_DIRECTORY
        self.new.mkdir(mode=0o700)
        self.manifest = {'patched_asar_sha256': 'base', 'main_steam_guard_version': 1,
                         'controlled_access_version': 1, 'controlled_gateway_sha256': 'gateway',
                         'controlled_network_sha256': 'network'}
        self.updated = {**self.manifest, 'ui_assets_version': 1,
                        'base_patched_asar_sha256': 'base', 'patched_asar_sha256': 'new'}
        self.write(self.base / 'manifest.json', self.manifest)
        self.write(self.new / 'manifest.json', self.updated)

    def write(self, path, data):
        path.write_text(json.dumps(data))
        path.chmod(0o600)

    def activate(self):
        self.write(self.root / ui_update.RECEIPT,
                   {'schema': 1, 'base_patched_asar_sha256': 'base', 'patched_asar_sha256': 'new'})

    def test_unselected_or_partial_update_keeps_original(self):
        self.assertEqual(ui_update.selected_session(self.root), self.base)

    def test_complete_update_requires_policy_and_signature_verification(self):
        self.activate()
        with patch.object(ui_update.controlled, 'proposal') as policy, patch.object(ui_update.cli, '_validate_launch_copy') as verify:
            self.assertEqual(ui_update.selected_session(self.root), self.new)
            policy.assert_called_once_with(self.new)
            verify.assert_called_once_with(self.new)
            verify.side_effect = HarnessError('bad signature')
            with self.assertRaises(HarnessError):
                ui_update.selected_session(self.root)

    def test_wrong_base_policy_version_or_receipt_fails_closed(self):
        self.activate()
        for key in ('base_patched_asar_sha256', 'patched_asar_sha256', 'ui_assets_version',
                    'main_steam_guard_version', 'controlled_gateway_sha256', 'controlled_network_sha256'):
            with self.subTest(key=key):
                self.write(self.new / 'manifest.json', {**self.updated, key: 'wrong'})
                with self.assertRaises(HarnessError):
                    ui_update.selected_session(self.root)
        self.write(self.new / 'manifest.json', self.updated)
        self.write(self.root / ui_update.RECEIPT, {'schema': 2})
        with self.assertRaises(HarnessError):
            ui_update.selected_session(self.root)

    def test_symlinked_receipt_or_update_directory_is_rejected(self):
        self.activate()
        real = self.root / 'receipt-private'
        (self.root / ui_update.RECEIPT).rename(real)
        (self.root / ui_update.RECEIPT).symlink_to(real)
        with self.assertRaises(OSError):
            ui_update.selected_session(self.root)
        (self.root / ui_update.RECEIPT).unlink()
        real.rename(self.root / ui_update.RECEIPT)
        realdir = self.root / 'redirected'
        self.new.rename(realdir)
        self.new.symlink_to(realdir, target_is_directory=True)
        with self.assertRaises(HarnessError):
            ui_update.selected_session(self.root)

    def test_tree_guard_allows_only_named_content_edits(self):
        app = self.root / 'app'
        app.mkdir()
        (app / 'native').write_bytes(b'native')
        (app / 'archive').write_bytes(b'old')
        (app / 'link').symlink_to('native')
        before = ui_update._tree(app)
        (app / 'archive').write_bytes(b'new')
        ui_update._only_changes(before, ui_update._tree(app), {'archive'})
        (app / 'native').write_bytes(b'modified')
        with self.assertRaises(HarnessError):
            ui_update._only_changes(before, ui_update._tree(app), {'archive'})
        (app / 'native').write_bytes(b'native')
        (app / 'archive').chmod(0o700)
        with self.assertRaises(HarnessError):
            ui_update._only_changes(before, ui_update._tree(app), {'archive'})

    def test_main_launch_uses_selected_update_after_backup_checks(self):
        # Reuse the existing orchestration fixture to verify the real launch call.
        from test_main_launcher import MainLauncherTests
        fixture = MainLauncherTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        _, _, _, _, run = fixture.patches()
        selected = fixture.root / 'companion-ui'
        with patch.object(ui_update, 'selected_session', return_value=selected):
            fixture.start()
        self.assertEqual(run.call_args.args[0], selected)


if __name__ == '__main__':
    unittest.main()
