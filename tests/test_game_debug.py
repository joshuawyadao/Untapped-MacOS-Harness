"""Synthetic copy and signing contracts; no vendor binary is executed or signed."""
import json
import os
import plistlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from harness.asar import HarnessError
from harness import game_debug as debug
from harness import game_launch as game


class DebugGameTests(unittest.TestCase):
    def setUp(self):
        if os.getuid() == 0:
            self.skipTest("debug-game preparation intentionally refuses root")
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.home = self.root / "test-home"
        self.home.mkdir()
        self.source = self.root / "Source.app"
        self.session = self.root / "debug-proposal"
        self._file(self.source / game.ASSEMBLY, b"synthetic assembly")
        self._file(self.source / game.EXECUTABLE, b"original executable")
        self._file(self.source / "Contents/_CodeSignature/CodeResources", b"original seal")
        self._file(self.source / "Contents/Resources/release_info.json",
                   json.dumps({"version": game.VERSION, "commit": game.COMMIT}).encode())
        self._file(self.source / "Contents/Resources/untouched.dat", b"immutable resource")
        self.patch(game.platform, "system", return_value="Darwin")
        self.patch(game, "ASSEMBLY_HASH", game.digest(self.source / game.ASSEMBLY))
        self.patch(debug, "ORIGINAL_TREE_SHA256", debug._tree_hash(game.tree_manifest(self.source)))
        self.native_settings = debug._settings
        self.settings = self.patch(debug, "_settings")
        self.patch(game, "verified_app", side_effect=self.verified_synthetic_app)

    def patch(self, obj, attribute, *args, **kwargs):
        started = mock.patch.object(obj, attribute, *args, **kwargs)
        result = started.start()
        self.addCleanup(started.stop)
        return result

    @staticmethod
    def _file(path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def verified_synthetic_app(self, app):
        app = Path(app)
        release = json.loads((app / "Contents/Resources/release_info.json").read_text())
        if release != {"version": game.VERSION, "commit": game.COMMIT}:
            raise HarnessError("Unsupported game build")
        if game.digest(app / game.ASSEMBLY) != game.ASSEMBLY_HASH:
            raise HarnessError("Unsupported assembly")
        return game.tree_manifest(app)

    def prepare(self):
        return debug.prepare(self.source, self.session)

    def signed(self):
        self.prepare()
        command = self.patch(debug, "_command", side_effect=self.sign_command)
        receipt = debug.sign(self.session, approved=True)
        self.assertEqual(command.call_count, 1)
        return receipt

    def sign_command(self, args):
        self.assertEqual(args[0:7], ["/usr/bin/codesign", "--force", "--sign", "-",
                                     "--options", "runtime", "--timestamp=none"])
        self.assertNotIn("--deep", args)
        self.assertEqual(args[-1], str(self.session / debug.APP))
        self._file(self.session / debug.APP / game.EXECUTABLE, b"signed executable")
        self._file(self.session / debug.APP / "Contents/_CodeSignature/CodeResources", b"signed seal")
        return SimpleNamespace(stdout=b"", stderr=b"", returncode=0)

    def test_rejects_same_version_and_assembly_with_changed_source_resource(self):
        self._file(self.source / "Contents/Resources/untouched.dat", b"unexpected resource")
        with self.assertRaisesRegex(HarnessError, "complete pinned source"):
            debug.prepare(self.source, self.session)
        self.assertFalse(self.session.exists())

    def test_preparation_yields_exact_proposal_without_signing(self):
        proposal = self.prepare()
        self.assertEqual(proposal["target"], str(self.session / debug.APP))
        self.assertTrue(proposal["requires_explicit_owner_approval"])
        self.assertFalse(proposal["signing_executed"])
        self.assertEqual(proposal["original_entitlements"], debug.ENTITLEMENTS)
        self.assertEqual(proposal["proposed_entitlements"], debug.DEBUG_ENTITLEMENTS)
        self.assertEqual(set(proposal["proposed_entitlements"]) - set(proposal["original_entitlements"]),
                         {"com.apple.security.get-task-allow"})
        self.assertEqual(plistlib.loads((self.session / "debug-game-entitlements.plist").read_bytes()),
                         debug.DEBUG_ENTITLEMENTS)
        self.assertEqual(game.tree_manifest(self.source), game.tree_manifest(self.session / debug.APP))
        self.assertFalse((self.session / debug.RECEIPT).exists())
        self.settings.assert_any_call(self.source, debug.ENTITLEMENTS)
        self.settings.assert_any_call(self.session / debug.APP, debug.ENTITLEMENTS)

    def test_sign_requires_explicit_approval_and_records_scoped_changes(self):
        self.prepare()
        with self.assertRaisesRegex(HarnessError, "Explicit owner approval"):
            debug.sign(self.session)
        self.assertFalse((self.session / debug.RECEIPT).exists())
        command = self.patch(debug, "_command", side_effect=self.sign_command)
        receipt = debug.sign(self.session, approved=True)
        self.assertEqual(command.call_count, 1)
        self.assertEqual(receipt["changed_files"], sorted(debug.SIGNING_FILES))
        self.assertEqual(receipt["entitlements"], debug.DEBUG_ENTITLEMENTS)
        self.assertEqual(debug.verify(self.session), receipt["signed_files"])
        self.settings.assert_any_call(self.session / debug.APP, debug.DEBUG_ENTITLEMENTS)
        self.assertEqual(game.tree_manifest(self.source)["Contents/Resources/untouched.dat"],
                         game.tree_manifest(self.session / debug.APP)["Contents/Resources/untouched.dat"])
        self.assertEqual((self.session / debug.RECEIPT).stat().st_mode & 0o777, 0o600)

    def test_rejects_changed_resource_mode_and_added_file(self):
        self.prepare()
        app = self.session / debug.APP
        self._file(app / "Contents/Resources/untouched.dat", b"tampered")
        with self.assertRaisesRegex(HarnessError, "differs"):
            debug.proposal(self.session)
        self._file(app / "Contents/Resources/untouched.dat", b"immutable resource")
        with self.patch(debug, "_command", side_effect=self.sign_command):
            debug.sign(self.session, approved=True)
        self._file(app / "Contents/Resources/extra.dat", b"new data")
        with self.assertRaisesRegex(HarnessError, "changed"):
            debug.verify(self.session)
        (app / "Contents/Resources/extra.dat").unlink()
        executable = app / game.EXECUTABLE
        executable.chmod(0o700)
        with self.assertRaisesRegex(HarnessError, "changed"):
            debug.verify(self.session)

    def test_refuses_tampered_missing_or_redirected_metadata(self):
        self.signed()
        receipt = self.session / debug.RECEIPT
        original = receipt.read_text()
        malformed = json.loads(original)
        malformed["entitlements"]["com.apple.security.get-task-allow"] = False
        receipt.write_text(json.dumps(malformed))
        with self.assertRaisesRegex(HarnessError, "receipt does not match"):
            debug.verify(self.session)
        receipt.write_text(original)
        receipt.unlink()
        with self.assertRaisesRegex(HarnessError, "metadata"):
            debug.verify(self.session)
        outside = self.root / "redirected.json"
        outside.write_text(original)
        receipt.symlink_to(outside)
        with self.assertRaisesRegex(HarnessError, "redirected"):
            debug.verify(self.session)
        receipt.unlink()
        receipt.write_text(original)
        baseline = self.session / debug.BASE
        old_baseline = baseline.read_text()
        altered = json.loads(old_baseline)
        altered["source_tree_sha256"] = "0" * 64
        baseline.write_text(json.dumps(altered))
        with self.assertRaisesRegex(HarnessError, "baseline"):
            debug.verify(self.session)

    def test_refuses_existing_or_overlapping_session_without_touching_source(self):
        self.prepare()
        with self.assertRaisesRegex(HarnessError, "fresh separate"):
            debug.prepare(self.source, self.session)
        overlapping = self.source / "child"
        with self.assertRaisesRegex(HarnessError, "fresh separate"):
            debug.prepare(self.source, overlapping)
        self.assertEqual((self.source / game.EXECUTABLE).read_bytes(), b"original executable")
        (self.session / debug.RECEIPT).write_text("{}")
        with self.assertRaisesRegex(HarnessError, "unsigned"):
            debug.proposal(self.session)

    def test_install_accepts_only_new_dedicated_test_session(self):
        self.signed()
        self.patch(game, "test_identity", return_value=("sts2test", self.home, self.root / "original-home"))
        wrong = self.home / "other"
        with self.assertRaisesRegex(HarnessError, "dedicated"):
            debug.install(self.session, wrong)
        target = self.home / debug.TEST_SESSION
        installed = debug.install(self.session, target)
        self.assertTrue(installed["debug_game"])
        self.assertEqual(debug.verify(target), debug.verify(self.session))
        manifest = json.loads((target / "manifest.json").read_text())
        self.assertTrue(manifest["game_signed"])
        self.assertEqual(manifest["files"], game.tree_manifest(target / debug.APP))
        with self.assertRaisesRegex(HarnessError, "dedicated"):
            debug.install(self.session, target)

    def test_launch_accepts_only_installed_signed_copy_and_exact_identity(self):
        self.signed()
        protected = self.root / "original-home"
        protected.mkdir()
        self.patch(game, "PROTECTED_HOME", protected)
        self.patch(game, "test_identity", return_value=("sts2test", self.home, protected))
        target = self.home / debug.TEST_SESSION
        debug.install(self.session, target)
        manifest = json.loads((target / "manifest.json").read_text())
        self.assertEqual(debug.verify_launch(target, manifest, self.home), manifest["files"])
        for change in ({"debug_game": False}, {"game_signed": False}, {"game_modified": False},
                       {"test_uid": os.getuid() + 1}, {"test_home": str(self.root)},
                       {"test_user": "somebody-else"}, {"original_home": str(self.root)}):
            with self.subTest(change=change), self.assertRaisesRegex(HarnessError, "exact installed"):
                debug.verify_launch(target, {**manifest, **change}, self.home)
        with self.assertRaisesRegex(HarnessError, "exact installed"):
            debug.verify_launch(self.home / "other", manifest, self.home)
        with self.assertRaisesRegex(HarnessError, "differs from signing receipt"):
            debug.verify_launch(target, {**manifest, "files": {}}, self.home)
        (target / debug.RECEIPT).unlink()
        with self.assertRaisesRegex(HarnessError, "metadata"):
            debug.verify_launch(target, manifest, self.home)

    def test_native_settings_rejects_wrong_entitlements_or_runtime(self):
        expected = debug.ENTITLEMENTS
        commands = []
        def command(args):
            commands.append(args)
            if "--entitlements" in args:
                return SimpleNamespace(stdout=plistlib.dumps({}).strip(), stderr=b"")
            return SimpleNamespace(stdout=b"", stderr=b"Signature=adhoc flags=0x10002(adhoc,runtime)")
        with self.patch(debug, "_command", side_effect=command):
            with self.assertRaisesRegex(HarnessError, "entitlements differ"):
                self.native_settings(self.source, expected)
        self.assertEqual(len(commands), 1)

        def no_runtime(args):
            if "--entitlements" in args:
                return SimpleNamespace(stdout=plistlib.dumps(expected), stderr=b"")
            return SimpleNamespace(stdout=b"", stderr=b"Signature=adhoc flags=0x2(adhoc)")
        with self.patch(debug, "_command", side_effect=no_runtime):
            with self.assertRaisesRegex(HarnessError, "Hardened Runtime"):
                self.native_settings(self.source, expected)


if __name__ == "__main__":
    unittest.main()
