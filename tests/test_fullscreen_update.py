"""Immutable full-screen layer selection and preparation, using synthetic bytes."""
import json
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from harness import fullscreen_update, login_update, main_launcher
from harness.asar import HarnessError, sha256


class FakeArchive:
    def __init__(self, data):
        self.data = data

    def read(self, _name):
        return self.data

    def rewrite(self, entries):
        return next(iter(entries.values()))


class FullscreenUpdateTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.root.chmod(0o700)
        self.source = self.root / 'companion-login-v2'
        self.source.mkdir(mode=0o700)
        self.selected = self.root / fullscreen_update.DIRECTORY
        self.base_bytes = b'original core'
        self.base_manifest = {
            'patched_asar_sha256': sha256(self.base_bytes),
            'ui_assets_version': 2,
            'base_patched_asar_sha256': 'original-asar',
            'remember_login_version': 1,
            'remember_login_revision': 2,
            'remember_login_base_sha256': 'ui-asar',
            'remember_login_helper_sha256': login_update.helper_hash(),
            'main_steam_guard_version': 1,
            'controlled_access_version': 1,
            'controlled_gateway_sha256': 'gateway',
            'controlled_network_sha256': 'network',
        }
        self.write(self.source / 'manifest.json', self.base_manifest)
        self.write(self.source / 'signing.json', {'schema': 1,
            'patched_asar_sha256': self.base_manifest['patched_asar_sha256']})

    @staticmethod
    def write(path, data):
        path.write_text(json.dumps(data) + '\n')
        path.chmod(0o600)

    def activate(self):
        self.selected.mkdir(mode=0o700)
        self.updated_bytes = self.base_bytes + b' panel'
        self.updated_manifest = {**self.base_manifest,
            'patched_asar_sha256': sha256(self.updated_bytes),
            'macos_fullscreen_version': 1,
            'macos_fullscreen_base_sha256': self.base_manifest['patched_asar_sha256']}
        self.write(self.selected / 'manifest.json', self.updated_manifest)
        self.write(self.selected / 'signing.json', {'schema': 1})
        self.write(self.selected / 'previous-signing.json',
                   json.loads((self.source / 'signing.json').read_text()))
        self.receipt = {'schema': 1, 'version': 1,
            'base_sha256': self.base_manifest['patched_asar_sha256'],
            'patched_asar_sha256': self.updated_manifest['patched_asar_sha256']}
        self.write(self.root / fullscreen_update.RECEIPT, self.receipt)

    def select(self):
        with patch.object(login_update, 'selected_session', return_value=self.source), \
             patch.object(fullscreen_update.cli, '_validate_launch_copy') as signature, \
             patch.object(fullscreen_update.controlled, 'proposal') as policy:
            result = fullscreen_update.selected_session(self.root)
        return result, signature, policy

    def test_no_layer_keeps_login_source_and_rejects_partial_directory(self):
        result, signature, policy = self.select()
        self.assertEqual(result, self.source)
        signature.assert_not_called()
        policy.assert_not_called()
        self.selected.mkdir(mode=0o700)
        with self.assertRaisesRegex(HarnessError, 'Incomplete'):
            self.select()

    def test_complete_layer_requires_signature_and_policy(self):
        self.activate()
        result, signature, policy = self.select()
        self.assertEqual(result, self.selected)
        signature.assert_called_once_with(self.selected)
        policy.assert_called_once_with(self.selected)
        with patch.object(login_update, 'selected_session', return_value=self.source), \
             patch.object(fullscreen_update.cli, '_validate_launch_copy',
                          side_effect=HarnessError('bad signature')):
            with self.assertRaisesRegex(HarnessError, 'bad signature'):
                fullscreen_update.selected_session(self.root)
        with patch.object(login_update, 'selected_session', return_value=self.source), \
             patch.object(fullscreen_update.cli, '_validate_launch_copy'), \
             patch.object(fullscreen_update.controlled, 'proposal',
                          side_effect=HarnessError('bad policy')):
            with self.assertRaisesRegex(HarnessError, 'bad policy'):
                fullscreen_update.selected_session(self.root)

    def test_claim_lineage_helper_and_policy_mismatches_fail_closed(self):
        self.activate()
        for path, original, changes in (
            (self.root / fullscreen_update.RECEIPT, self.receipt,
             [('schema', True), ('version', True), ('version', 2),
              ('base_sha256', 'other'), ('patched_asar_sha256', 'other')]),
            (self.selected / 'manifest.json', self.updated_manifest,
             [('macos_fullscreen_version', True), ('macos_fullscreen_version', 2),
              ('macos_fullscreen_base_sha256', 'other'), ('patched_asar_sha256', 'other'),
              ('ui_assets_version', 1), ('remember_login_version', 2),
              ('remember_login_version', True), ('remember_login_version', 1.0),
              ('remember_login_revision', 1), ('remember_login_base_sha256', 'other'),
              ('remember_login_helper_sha256', 'other'),
              ('main_steam_guard_version', True), ('main_steam_guard_version', 1.0),
              ('controlled_gateway_sha256', 'other'),
              ('controlled_network_sha256', 'other')]),
            (self.selected / 'previous-signing.json',
             json.loads((self.source / 'signing.json').read_text()),
             [('patched_asar_sha256', 'other'), ('schema', True), ('schema', 1.0)]),
        ):
            for key, value in changes:
                with self.subTest(file=path.name, key=key, value=value):
                    self.write(path, {**original, key: value})
                    with self.assertRaises(HarnessError):
                        self.select()
            self.write(path, original)
        self.write(self.source / 'manifest.json', {**self.base_manifest,
            'controlled_gateway_sha256': 'changed'})
        with self.assertRaises(HarnessError):
            self.select()

    def test_redirected_receipt_and_open_directory_are_rejected(self):
        self.activate()
        receipt = self.root / fullscreen_update.RECEIPT
        moved = self.root / 'private-receipt'
        receipt.rename(moved)
        receipt.symlink_to(moved)
        with self.assertRaises((OSError, HarnessError)):
            self.select()
        receipt.unlink()
        moved.rename(receipt)
        self.selected.chmod(0o755)
        with self.assertRaises(HarnessError):
            self.select()

    def test_fresh_claim_is_idempotent_but_malformed_claim_fails(self):
        fresh = {**self.base_manifest, 'macos_fullscreen_version': 1,
                 'macos_fullscreen_base_sha256': sha256(b'original prepatch')}
        self.write(self.source / 'manifest.json', fresh)
        asar = self.source / 'Companion.app/Contents/Resources/app.asar'
        asar.parent.mkdir(parents=True)
        asar.write_bytes(fullscreen_update.fullscreen_patch.WINDOW_NEW.encode())
        with patch.object(fullscreen_update, 'Archive', FakeArchive):
            result, signature, policy = self.select()
        self.assertEqual(result, self.source)
        signature.assert_called_once_with(self.source)
        policy.assert_called_once_with(self.source)
        asar.write_bytes(fullscreen_update.fullscreen_patch.WINDOW_OLD.encode())
        with patch.object(fullscreen_update, 'Archive', FakeArchive):
            with self.assertRaisesRegex(HarnessError, 'patch is absent'):
                self.select()
        for claim in (True, 2, '1', None):
            with self.subTest(claim=claim):
                self.write(self.source / 'manifest.json', {**fresh,
                    'macos_fullscreen_version': claim})
                with self.assertRaises(HarnessError):
                    self.select()

    def _install_fixture(self):
        app = self.source / 'Companion.app/Contents'
        (app / 'Resources').mkdir(parents=True)
        (app / 'MacOS').mkdir()
        (app / '_CodeSignature').mkdir()
        (app / 'Resources/app.asar').write_bytes(self.base_bytes)
        (app / fullscreen_update.signing.EXECUTABLE).write_bytes(b'executable')
        (app / '_CodeSignature/CodeResources').write_bytes(b'seal')
        return app / 'Resources/app.asar'

    def _install_patches(self, stack):
        stack.enter_context(patch.object(main_launcher, '_prepared',
                                         return_value=(self.root, None, None)))
        stack.enter_context(patch.object(login_update, 'selected_session', return_value=self.source))
        stack.enter_context(patch.object(fullscreen_update, 'Archive', FakeArchive))
        stack.enter_context(patch.object(fullscreen_update.fullscreen_patch,
                                         'patch_core', side_effect=lambda text: text + ' panel'))
        stack.enter_context(patch.object(fullscreen_update.cli, '_validate_launch_copy'))
        stack.enter_context(patch.object(fullscreen_update.controlled, 'proposal'))
        stack.enter_context(patch.object(fullscreen_update.signing, '_entitlements'))
        stack.enter_context(patch.object(fullscreen_update.signing, 'verify_signed_copy'))
        stack.enter_context(patch.object(fullscreen_update.signing, '_check_payloads'))

    def test_install_preserves_source_and_publishes_bound_receipt(self):
        asar = self._install_fixture()
        original_tree = fullscreen_update.ui_update._tree(self.source / 'Companion.app')
        with ExitStack() as stack:
            self._install_patches(stack)
            signer = stack.enter_context(patch.object(fullscreen_update.signing, '_run_codesign'))
            result = fullscreen_update.install_main()
            again = fullscreen_update.install_main()
        self.assertEqual(result['effective'], 'NEXT_LAUNCH')
        self.assertTrue(again['already_installed'])
        self.assertEqual(asar.read_bytes(), self.base_bytes)
        self.assertEqual(fullscreen_update.ui_update._tree(self.source / 'Companion.app'), original_tree)
        manifest = json.loads((self.selected / 'manifest.json').read_text())
        self.assertEqual(manifest['macos_fullscreen_base_sha256'], sha256(self.base_bytes))
        self.assertEqual(manifest['patched_asar_sha256'], sha256(self.base_bytes + b' panel'))
        self.assertEqual((self.selected / 'Companion.app/Contents/Resources/app.asar').read_bytes(),
                         self.base_bytes + b' panel')
        self.assertEqual(json.loads((self.root / fullscreen_update.RECEIPT).read_text()), {
            'schema': 1, 'version': 1, 'base_sha256': sha256(self.base_bytes),
            'patched_asar_sha256': sha256(self.base_bytes + b' panel')})
        signer.assert_called_once()

    def test_signing_failure_retains_stage_and_does_not_publish(self):
        self._install_fixture()
        with ExitStack() as stack:
            self._install_patches(stack)
            stack.enter_context(patch.object(fullscreen_update.signing, '_run_codesign',
                                             side_effect=HarnessError('sign failed')))
            with self.assertRaisesRegex(HarnessError, 'sign failed'):
                fullscreen_update.install_main()
        self.assertFalse(self.selected.exists())
        self.assertFalse((self.root / fullscreen_update.RECEIPT).exists())
        self.assertEqual(len(list(self.root.glob('fullscreen-preparation-*'))), 1)

    def test_interrupted_publication_is_not_selected_or_overwritten(self):
        self._install_fixture()
        self.selected.mkdir(mode=0o700)
        with patch.object(login_update, 'selected_session', return_value=self.source), \
             patch.object(main_launcher, '_prepared', return_value=(self.root, None, None)):
            with self.assertRaisesRegex(HarnessError, 'Incomplete'):
                fullscreen_update.install_main()
            with self.assertRaisesRegex(HarnessError, 'Incomplete'):
                fullscreen_update.selected_session(self.root)


if __name__ == '__main__':
    unittest.main()
