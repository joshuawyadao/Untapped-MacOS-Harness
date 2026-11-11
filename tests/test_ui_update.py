"""Offline update selection and preservation guards, without vendor data."""
import json
import os
import tempfile
import unittest
from contextlib import ExitStack
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
        self.write(self.new / 'signing.json', {'schema': 1})

    def write(self, path, data):
        path.write_text(json.dumps(data))
        path.chmod(0o600)

    def activate(self):
        self.write(self.root / ui_update.RECEIPT,
                   {'schema': 1, 'base_patched_asar_sha256': 'base', 'patched_asar_sha256': 'new'})

    def activate_current(self):
        current = self.root / ui_update.CURRENT_DIRECTORY
        current.mkdir(mode=0o700)
        self.write(current / 'manifest.json', {**self.updated, 'ui_assets_version': 2,
                   'patched_asar_sha256': 'current'})
        self.write(current / 'signing.json', {'schema': 1})
        self.write(self.root / ui_update.CURRENT_RECEIPT,
                   {'schema': 1, 'ui_assets_version': 2,
                    'base_patched_asar_sha256': 'base', 'patched_asar_sha256': 'current'})
        return current

    def installation_fixture(self):
        self.activate()
        (self.root / 'activation.json').write_text('{}')
        contents = self.new / 'Companion.app' / 'Contents'
        (contents / 'Resources').mkdir(parents=True)
        (contents / 'MacOS').mkdir()
        (contents / '_CodeSignature').mkdir()
        (contents / 'Resources' / 'app.asar').write_bytes(b'legacy asar')
        (contents / ui_update.signing.EXECUTABLE).write_bytes(b'signed executable')
        (contents / '_CodeSignature' / 'CodeResources').write_bytes(b'code resources')
        return {name: (self.root / name).read_bytes() for name in (
            ui_update.RECEIPT, ui_update.UPDATE_DIRECTORY + '/manifest.json',
            ui_update.UPDATE_DIRECTORY + '/signing.json',
            ui_update.UPDATE_DIRECTORY + '/Companion.app/Contents/Resources/app.asar')}

    def fake_prepare_current(self, stage):
        archive = stage / 'Companion.app/Contents/Resources/app.asar'
        archive.write_bytes(b'current asar')
        self.write(stage / 'manifest.json', {**self.updated, 'ui_assets_version': 2,
                   'patched_asar_sha256': 'current'})
        (stage / 'signing.json').rename(stage / 'previous-signing.json')

    def install_patches(self, stack):
        stack.enter_context(patch.object(main_launcher, '_prepared', return_value=(self.root, None, None)))
        stack.enter_context(patch.object(ui_update.controlled, 'proposal'))
        stack.enter_context(patch.object(ui_update.cli, '_validate_launch_copy'))
        stack.enter_context(patch.object(ui_update.signing, '_entitlements'))
        stack.enter_context(patch.object(ui_update.signing, 'verify_signed_copy'))
        stack.enter_context(patch.object(ui_update.signing, '_check_payloads'))
        return stack.enter_context(patch('harness.ui_assets.prepare', side_effect=self.fake_prepare_current))

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

    def test_legacy_receipt_accepts_explicit_assets_version_one(self):
        self.activate()
        self.write(self.root / ui_update.RECEIPT,
                   {'schema': 1, 'ui_assets_version': 1,
                    'base_patched_asar_sha256': 'base', 'patched_asar_sha256': 'new'})
        with patch.object(ui_update.controlled, 'proposal'), patch.object(ui_update.cli, '_validate_launch_copy'):
            self.assertEqual(ui_update.selected_session(self.root), self.new)

    def test_complete_current_update_takes_precedence_over_legacy(self):
        self.activate()
        current = self.activate_current()
        with patch.object(ui_update.controlled, 'proposal') as policy, patch.object(ui_update.cli, '_validate_launch_copy') as verify:
            self.assertEqual(ui_update.selected_session(self.root), current)
            policy.assert_called_once_with(current)
            verify.assert_called_once_with(current)
            verify.side_effect = HarnessError('bad signature')
            with self.assertRaisesRegex(HarnessError, 'bad signature'):
                ui_update.selected_session(self.root)

    def test_incomplete_current_directory_does_not_replace_legacy(self):
        self.activate()
        current = self.root / ui_update.CURRENT_DIRECTORY
        current.mkdir(mode=0o700)
        self.write(current / 'manifest.json', {**self.updated, 'ui_assets_version': 2})
        with patch.object(ui_update.controlled, 'proposal'), patch.object(ui_update.cli, '_validate_launch_copy'):
            self.assertEqual(ui_update.selected_session(self.root), self.new)

    def test_current_receipt_or_manifest_mismatch_fails_closed(self):
        self.activate()
        current = self.activate_current()
        with patch.object(ui_update.controlled, 'proposal'), patch.object(ui_update.cli, '_validate_launch_copy'):
            original = json.loads((current / 'manifest.json').read_text())
            for key, value in (('ui_assets_version', 1), ('ui_assets_version', True),
                               ('ui_assets_version', 2.0), ('ui_assets_version', None),
                               ('base_patched_asar_sha256', 'other'),
                               ('patched_asar_sha256', 'other'), ('controlled_gateway_sha256', 'other')):
                with self.subTest(key=key):
                    self.write(current / 'manifest.json', {**original, key: value})
                    with self.assertRaises(HarnessError):
                        ui_update.selected_session(self.root)
            self.write(current / 'manifest.json', original)
            missing_version = dict(original)
            missing_version.pop('ui_assets_version')
            self.write(current / 'manifest.json', missing_version)
            with self.assertRaises(HarnessError):
                ui_update.selected_session(self.root)
            self.write(current / 'manifest.json', original)
            (current / 'signing.json').unlink()
            with self.assertRaises((OSError, HarnessError)):
                ui_update.selected_session(self.root)
            self.write(current / 'signing.json', {'schema': 1})
            for record in ({'schema': 2, 'ui_assets_version': 2,
                            'base_patched_asar_sha256': 'base', 'patched_asar_sha256': 'current'},
                           {'schema': 1, 'ui_assets_version': 1,
                            'base_patched_asar_sha256': 'base', 'patched_asar_sha256': 'current'},
                           {'schema': 1, 'base_patched_asar_sha256': 'base',
                            'patched_asar_sha256': 'current'}):
                with self.subTest(record=record):
                    self.write(self.root / ui_update.CURRENT_RECEIPT, record)
                    with self.assertRaises(HarnessError):
                        ui_update.selected_session(self.root)

    def test_failed_upgrade_preserves_legacy_selection_and_receipt(self):
        self.activate()
        (self.root / 'activation.json').write_text('{}')
        app = self.new / 'Companion.app'
        app.mkdir()
        (app / 'payload').write_bytes(b'legacy')
        self.write(self.new / 'signing.json', {'schema': 1})
        receipt = self.root / ui_update.RECEIPT
        original_receipt = receipt.read_bytes()
        with patch.object(main_launcher, '_prepared', return_value=(self.root, None, None)), \
             patch.object(ui_update.controlled, 'proposal'), \
             patch.object(ui_update.cli, '_validate_launch_copy'), \
             patch('harness.ui_assets.prepare', side_effect=HarnessError('asset failure')):
            self.assertEqual(ui_update.selected_session(self.root), self.new)
            with self.assertRaisesRegex(HarnessError, 'asset failure'):
                ui_update.install_main()
            self.assertEqual(ui_update.selected_session(self.root), self.new)
        self.assertEqual(receipt.read_bytes(), original_receipt)
        self.assertFalse((self.root / ui_update.CURRENT_RECEIPT).exists())
        self.assertFalse((self.root / ui_update.CURRENT_DIRECTORY).exists())

    def test_install_publishes_current_receipt_and_preserves_legacy(self):
        original = self.installation_fixture()
        with ExitStack() as stack:
            prepare = self.install_patches(stack)
            stack.enter_context(patch.object(ui_update.signing, '_run_codesign'))
            result = ui_update.install_main()
            self.assertEqual(result['ui_assets_version'], 2)
            current = self.root / ui_update.CURRENT_DIRECTORY
            self.assertEqual(ui_update.selected_session(self.root), current)
            self.assertEqual(json.loads((self.root / ui_update.CURRENT_RECEIPT).read_text()),
                             {'schema': 1, 'ui_assets_version': 2,
                              'base_patched_asar_sha256': 'base', 'patched_asar_sha256': 'current'})
            self.assertEqual((current / 'Companion.app/Contents/Resources/app.asar').read_bytes(), b'current asar')
            self.assertTrue((current / 'previous-signing.json').is_file())
            self.assertTrue(ui_update.install_main()['already_installed'])
            prepare.assert_called_once()
        for name, data in original.items():
            self.assertEqual((self.root / name).read_bytes(), data, name)

    def test_signing_failure_keeps_legacy_selected(self):
        original = self.installation_fixture()
        with ExitStack() as stack:
            self.install_patches(stack)
            stack.enter_context(patch.object(ui_update.signing, '_run_codesign',
                                            side_effect=HarnessError('signing failed')))
            with self.assertRaisesRegex(HarnessError, 'signing failed'):
                ui_update.install_main()
            self.assertEqual(ui_update.selected_session(self.root), self.new)
        for name, data in original.items():
            self.assertEqual((self.root / name).read_bytes(), data, name)
        self.assertFalse((self.root / ui_update.CURRENT_RECEIPT).exists())
        self.assertFalse((self.root / ui_update.CURRENT_DIRECTORY).exists())

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
