"""Remember-login selection and preparation guards with synthetic app bytes."""

import json
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from harness import login_update, main_launcher, remember_patch, ui_update
from harness.asar import HarnessError, sha256


class FakeArchive:
    def __init__(self, data):
        self.data = data

    def read(self, _name):
        return self.data

    def rewrite(self, entries):
        return next(iter(entries.values()))


class LoginUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.root.chmod(0o700)
        self.base = self.root / 'companion-ui'
        self.base.mkdir(mode=0o700)
        self.selected = self.root / login_update.DIRECTORY
        self.selected.mkdir(mode=0o700)
        self.base_manifest = {
            'patched_asar_sha256': 'base-asar',
            'ui_assets_version': 2,
            'base_patched_asar_sha256': 'original-asar',
            'main_steam_guard_version': 1,
            'controlled_access_version': 1,
            'controlled_gateway_sha256': 'gateway',
            'controlled_network_sha256': 'network',
        }
        self.login_manifest = {
            **self.base_manifest,
            'patched_asar_sha256': 'login-asar',
            'remember_login_version': 1,
            'remember_login_base_sha256': 'base-asar',
            'remember_login_helper_sha256': login_update.helper_hash(),
        }
        self.receipt = {
            'schema': 1, 'base_sha256': 'base-asar',
            'patched_asar_sha256': 'login-asar',
        }
        self.write(self.base / 'manifest.json', self.base_manifest)
        self.write(self.selected / 'manifest.json', self.login_manifest)
        self.write(self.selected / 'signing.json', {'schema': 1})

    @staticmethod
    def write(path, data):
        path.write_text(json.dumps(data))
        path.chmod(0o600)

    def activate(self):
        self.write(self.root / login_update.RECEIPT, self.receipt)

    def select(self):
        with patch.object(ui_update, 'selected_session', return_value=self.base), \
             patch.object(login_update.cli, '_validate_launch_copy') as verify, \
             patch.object(login_update.controlled, 'proposal') as policy:
            result = login_update.selected_session(self.root)
        return result, verify, policy

    def test_no_receipt_keeps_existing_ui_selection(self):
        result, verify, policy = self.select()
        self.assertEqual(result, self.base)
        verify.assert_not_called()
        policy.assert_not_called()

    def test_complete_receipt_requires_signature_and_policy(self):
        self.activate()
        result, verify, policy = self.select()
        self.assertEqual(result, self.selected)
        verify.assert_called_once_with(self.selected)
        policy.assert_called_once_with(self.selected)
        with patch.object(ui_update, 'selected_session', return_value=self.base), \
             patch.object(login_update.cli, '_validate_launch_copy',
                          side_effect=HarnessError('invalid signature')):
            with self.assertRaisesRegex(HarnessError, 'invalid signature'):
                login_update.selected_session(self.root)
        with patch.object(ui_update, 'selected_session', return_value=self.base), \
             patch.object(login_update.cli, '_validate_launch_copy'), \
             patch.object(login_update.controlled, 'proposal',
                          side_effect=HarnessError('invalid policy')):
            with self.assertRaisesRegex(HarnessError, 'invalid policy'):
                login_update.selected_session(self.root)

    def test_receipt_base_helper_and_policy_mismatch_fail_closed(self):
        self.activate()
        for path, original, changes in (
            (self.root / login_update.RECEIPT, self.receipt,
             [('schema', True), ('base_sha256', 'other'),
              ('patched_asar_sha256', 'other')]),
            (self.selected / 'manifest.json', self.login_manifest,
             [('remember_login_version', True), ('remember_login_version', 2),
              ('remember_login_base_sha256', 'other'),
              ('remember_login_helper_sha256', 'other'),
              ('patched_asar_sha256', 'other'),
              ('ui_assets_version', 1),
              ('base_patched_asar_sha256', 'other'),
              ('main_steam_guard_version', 2),
              ('controlled_access_version', 2),
              ('controlled_gateway_sha256', 'other'),
              ('controlled_network_sha256', 'other')]),
        ):
            for key, value in changes:
                with self.subTest(file=path.name, key=key, value=value):
                    self.write(path, {**original, key: value})
                    with self.assertRaises(HarnessError):
                        self.select()
            self.write(path, original)

    def test_partial_or_redirected_selection_is_rejected(self):
        self.activate()
        (self.selected / 'signing.json').unlink()
        with self.assertRaises((OSError, HarnessError)):
            self.select()
        self.write(self.selected / 'signing.json', {'schema': 1})
        target = self.root / 'receipt-private'
        (self.root / login_update.RECEIPT).rename(target)
        (self.root / login_update.RECEIPT).symlink_to(target)
        with self.assertRaises((OSError, HarnessError)):
            self.select()
        (self.root / login_update.RECEIPT).unlink()
        target.rename(self.root / login_update.RECEIPT)
        self.selected.chmod(0o755)
        with self.assertRaises(HarnessError):
            self.select()

    def test_patch_exact_anchor_and_default_off(self):
        source = ('prefix\n' + remember_patch.ANCHOR + '\n'
                  + remember_patch.KEYTAR + '\nother\n')
        patched = remember_patch.inject(source)
        self.assertEqual(patched.count(remember_patch.ANCHOR), 1)
        self.assertIn('harnessRememberKeytar || memoryKeytar', patched)
        self.assertNotIn(remember_patch.KEYTAR, patched)
        self.assertIn('UNTAPPED_HARNESS_REMEMBER_LOGIN === "1"', patched)
        self.assertIn('UNTAPPED_HARNESS_MAIN_ACCOUNT === "1"', patched)
        self.assertIn('if (controlled &&', patched)
        for broken in (source.replace(remember_patch.ANCHOR, ''),
                       source.replace(remember_patch.KEYTAR, ''),
                       source + remember_patch.ANCHOR,
                       source + remember_patch.KEYTAR):
            with self.subTest(broken=broken[-40:]), self.assertRaises(HarnessError):
                remember_patch.inject(broken)

    def _install_fixture(self):
        # Installation starts from the base; the selected directory above is only
        # used by selection tests and must not exist before preparation.
        for child in self.selected.iterdir():
            child.unlink()
        self.selected.rmdir()
        app = self.base / 'Companion.app' / 'Contents'
        (app / 'Resources').mkdir(parents=True)
        (app / 'MacOS').mkdir()
        (app / '_CodeSignature').mkdir()
        source = (remember_patch.ANCHOR + '\n' + remember_patch.KEYTAR + '\n')
        (app / 'Resources/app.asar').write_bytes(source.encode())
        (app / login_update.signing.EXECUTABLE).write_bytes(b'signed executable')
        (app / '_CodeSignature/CodeResources').write_bytes(b'seal')
        self.write(self.base / 'signing.json', {'schema': 1,
                   'patched_asar_sha256': self.base_manifest['patched_asar_sha256']})
        return source, (self.base / 'Companion.app/Contents/Resources/app.asar').read_bytes()

    def _install_patches(self, stack):
        stack.enter_context(patch.object(main_launcher, '_prepared',
                                         return_value=(self.root, None, None)))
        stack.enter_context(patch.object(ui_update, 'selected_session',
                                         return_value=self.base))
        stack.enter_context(patch.object(login_update, 'Archive', FakeArchive))
        stack.enter_context(patch.object(login_update.cli, '_validate_launch_copy'))
        stack.enter_context(patch.object(login_update.controlled, 'proposal'))
        stack.enter_context(patch.object(login_update.ui_update, '_only_changes'))
        stack.enter_context(patch.object(login_update.signing, '_entitlements'))
        stack.enter_context(patch.object(login_update.signing, 'verify_signed_copy'))
        stack.enter_context(patch.object(login_update.signing, '_check_payloads'))

    def test_install_publishes_bound_receipt_and_preserves_source(self):
        source, original = self._install_fixture()
        with ExitStack() as stack:
            self._install_patches(stack)
            signer = stack.enter_context(patch.object(login_update.signing, '_run_codesign'))
            result = login_update.install_main()
        self.assertEqual(result['effective'], 'NEXT_LAUNCH')
        self.assertFalse(result['credentials_saved'])
        self.assertFalse(result['runtime_network_expanded'])
        self.assertEqual((self.base / 'Companion.app/Contents/Resources/app.asar').read_bytes(), original)
        self.assertTrue((self.selected / 'previous-signing.json').is_file())
        patched = remember_patch.inject(source).encode()
        self.assertEqual((self.selected / 'Companion.app/Contents/Resources/app.asar').read_bytes(), patched)
        manifest = json.loads((self.selected / 'manifest.json').read_text())
        self.assertEqual(manifest['patched_asar_sha256'], sha256(patched))
        self.assertEqual(manifest['remember_login_base_sha256'], self.base_manifest['patched_asar_sha256'])
        self.assertEqual(manifest['remember_login_helper_sha256'], login_update.helper_hash())
        self.assertEqual(json.loads((self.root / login_update.RECEIPT).read_text()), {
            'schema': 1, 'base_sha256': self.base_manifest['patched_asar_sha256'],
            'patched_asar_sha256': sha256(patched),
        })
        signer.assert_called_once()
        self.assertIn('--entitlements', signer.call_args.args[0])
        selected, _, _ = self.select()
        self.assertEqual(selected, self.selected)

    def test_signing_failure_preserves_source_and_does_not_publish_receipt(self):
        _, original = self._install_fixture()
        with ExitStack() as stack:
            self._install_patches(stack)
            stack.enter_context(patch.object(login_update.signing, '_run_codesign',
                                             side_effect=HarnessError('signing failed')))
            with self.assertRaisesRegex(HarnessError, 'signing failed'):
                login_update.install_main()
        self.assertEqual((self.base / 'Companion.app/Contents/Resources/app.asar').read_bytes(), original)
        self.assertFalse((self.root / login_update.RECEIPT).exists())
        self.assertFalse(self.selected.exists())


if __name__ == '__main__':
    unittest.main()
