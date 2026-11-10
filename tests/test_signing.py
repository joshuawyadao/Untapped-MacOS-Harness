"""Signing contract tests using synthetic app bytes and a stubbed codesign."""
import copy
import json
import plistlib
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from harness import signing
from harness.asar import HarnessError, sha256


class SigningTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "Official.app"
        self.session = self.root / "session"
        self.app = self.session / "Companion.app"
        self.original_executable = b"original executable"
        self.asar = b"modified synthetic archive"
        self.framework = b"synthetic Electron framework"
        self.native = b"synthetic native reader"
        self._write(self.source / "Contents" / signing.EXECUTABLE, self.original_executable)
        self._write(self.app / "Contents" / signing.EXECUTABLE, self.original_executable)
        self._write(self.app / "Contents/Resources/app.asar", self.asar)
        self._write(self.app / "Contents" / signing.FRAMEWORK, self.framework)
        self._write(self.app / "Contents/Resources/app.asar.unpacked" / signing.SCRY, self.native)
        self._write(self.app / "Contents/Info.plist", plistlib.dumps({"CFBundleName": "synthetic"}))
        self._write(self.app / "Contents/_CodeSignature/CodeResources", b"original seal")
        self.manifest = {
            "schema": 1, "source_signature_valid": True,
            "app_asar_sha256": "a" * 64,
            "patched_asar_sha256": sha256(self.asar),
        }
        (self.session / "manifest.json").write_text(json.dumps(self.manifest))
        pins = {
            "ASAR_SHA256": "a" * 64,
            "EXECUTABLE_SHA256": sha256(self.original_executable),
            "FRAMEWORK_SHA256": sha256(self.framework),
            "SCRY_SHA256": sha256(self.native),
        }
        self.pin_patch = mock.patch.multiple(signing, **pins)
        self.pin_patch.start()
        self.addCleanup(self.pin_patch.stop)
        self.platform_patch = mock.patch.object(signing.platform, "system", return_value="Darwin")
        self.platform_patch.start()
        self.addCleanup(self.platform_patch.stop)
        self.calls = []
        self.entitlements = copy.deepcopy(signing.ENTITLEMENTS)
        self.codesign_patch = mock.patch.object(signing.subprocess, "run", side_effect=self._codesign)
        self.codesign_patch.start()
        self.addCleanup(self.codesign_patch.stop)

    @staticmethod
    def _write(path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def _codesign(self, command, **_kwargs):
        self.calls.append(command)
        if "-d" in command:
            self.assertIn("--arch", command)
            self.assertIn(command[command.index("--arch") + 1], ("arm64", "x86_64"))
            return subprocess.CompletedProcess(command, 0, stdout=plistlib.dumps(self.entitlements))
        if "--force" in command:
            self.assertEqual(Path(command[-1]).resolve(), self.app.resolve())
            (self.app / "Contents" / signing.EXECUTABLE).write_bytes(b"ad hoc signed executable")
            return subprocess.CompletedProcess(command, 0, stdout=b"")
        self.assertEqual(command[1:4], ["--verify", "--deep", "--strict"])
        return subprocess.CompletedProcess(command, 0, stdout=b"")

    def test_unsigned_copy_uses_original_executable_pin_without_codesign(self):
        result = signing.expected_executable_hash(self.session, self.manifest)
        self.assertEqual(result, sha256(self.original_executable))
        self.assertEqual(self.calls, [])

    def test_approval_gate_precedes_any_file_or_codesign_work(self):
        with self.assertRaisesRegex(HarnessError, "Explicit owner approval"):
            signing.sign_copy(self.session)
        self.assertEqual(self.calls, [])
        self.assertFalse((self.session / "companion-entitlements.plist").exists())
        self.assertFalse((self.session / "signing.json").exists())

    def test_failed_signing_preserves_bounded_reason_without_success_receipt(self):
        def failing_codesign(command, **kwargs):
            if "--force" in command:
                raise subprocess.CalledProcessError(
                    1, command, stderr=b"sealed resource mismatch: " + b"x" * 3000)
            return self._codesign(command, **kwargs)

        with mock.patch.object(signing.subprocess, "run", side_effect=failing_codesign):
            with self.assertRaisesRegex(HarnessError, "sealed resource mismatch") as failure:
                signing.sign_copy(self.session, approved=True)
        self.assertLessEqual(len(str(failure.exception)), 2020)
        self.assertFalse((self.session / "signing.json").exists())
        self.assertEqual((self.app / "Contents" / signing.EXECUTABLE).read_bytes(), self.original_executable)

    def test_proposal_is_reviewable_and_does_not_sign(self):
        proposal = signing.signing_proposal(self.session)
        command = proposal["command"]
        self.assertEqual(proposal["signing_executed"], False)
        self.assertEqual(proposal["entitlements"], signing.ENTITLEMENTS)
        self.assertEqual(plistlib.loads((self.session / "companion-entitlements.plist").read_bytes()), signing.ENTITLEMENTS)
        self.assertEqual(command[0:4], ["/usr/bin/codesign", "--force", "--sign", "-"])
        self.assertIn("--options", command)
        self.assertIn("runtime", command)
        self.assertNotIn("--deep", command)
        self.assertNotIn("--entitlements=", command)
        self.assertEqual(Path(command[-1]).resolve(), self.app.resolve())
        self.assertEqual((self.app / "Contents" / signing.EXECUTABLE).read_bytes(), self.original_executable)
        self.assertEqual(len(self.calls), 2)
        self.assertTrue(all("--arch" in command for command in self.calls))

    def test_approved_signing_verifies_original_entitlements_and_binds_receipt(self):
        receipt = signing.sign_copy(self.session, approved=True)
        signed = sha256(b"ad hoc signed executable")
        self.assertEqual(receipt["signed_executable_sha256"], signed)
        self.assertEqual(signing.expected_executable_hash(self.session, self.manifest), signed)
        self.assertEqual(json.loads((self.session / "signing.json").read_text()), receipt)
        self.assertEqual((self.source / "Contents" / signing.EXECUTABLE).read_bytes(), self.original_executable)
        self.assertEqual((self.app / "Contents" / signing.FRAMEWORK).read_bytes(), self.framework)
        self.assertEqual((self.app / "Contents/Resources/app.asar.unpacked" / signing.SCRY).read_bytes(), self.native)
        self.assertEqual((self.app / "Contents/Resources/app.asar").read_bytes(), self.asar)
        sign = next(command for command in self.calls if "--force" in command)
        self.assertNotIn("--deep", sign)
        self.assertEqual(sum("--verify" in command for command in self.calls), 1)
        self.assertEqual(sum("--arch" in command for command in self.calls), 4)
        for changed in ("original_executable_sha256", "patched_asar_sha256", "entitlements",
                        "scope", "hardened_runtime", "nested_code_resigned"):
            altered = copy.deepcopy(receipt)
            altered[changed] = "wrong"
            (self.session / "signing.json").write_text(json.dumps(altered))
            with self.subTest(changed=changed), self.assertRaisesRegex(HarnessError, "receipt"):
                signing.expected_executable_hash(self.session, self.manifest)

    def test_unknown_entitlement_fails_before_any_signing(self):
        self.entitlements["com.apple.security.get-task-allow"] = True
        with self.assertRaisesRegex(HarnessError, "five inspected originals"):
            signing.sign_copy(self.session, approved=True)
        self.assertFalse(any("--force" in command for command in self.calls))
        self.assertFalse((self.session / "signing.json").exists())

    def test_changed_nested_payload_or_source_pin_fails_before_signing(self):
        native = self.app / "Contents/Resources/app.asar.unpacked" / signing.SCRY
        native.write_bytes(b"changed native reader")
        with self.assertRaisesRegex(HarnessError, "Prepared payload changed"):
            signing.sign_copy(self.session, approved=True)
        self.assertEqual(self.calls, [])
        native.write_bytes(self.native)
        bad_manifest = dict(self.manifest, app_asar_sha256="b" * 64)
        (self.session / "manifest.json").write_text(json.dumps(bad_manifest))
        with self.assertRaisesRegex(HarnessError, "verified pinned-source"):
            signing.sign_copy(self.session, approved=True)
        self.assertEqual(self.calls, [])

    def test_previously_launched_or_signed_session_is_rejected(self):
        (self.session / "launch.json").write_text("{}")
        with self.assertRaisesRegex(HarnessError, "fresh unlaunched"):
            signing.signing_proposal(self.session)
        (self.session / "launch.json").unlink()
        (self.session / "signing.json").write_text("{}")
        with self.assertRaisesRegex(HarnessError, "fresh unlaunched"):
            signing.signing_proposal(self.session)
        self.assertEqual(self.calls, [])

    def test_symlink_target_outside_disposable_session_is_rejected(self):
        shutil.rmtree(self.app)
        self.app.symlink_to(self.source, target_is_directory=True)
        with self.assertRaisesRegex(HarnessError, "disposable app outside"):
            signing.signing_proposal(self.session)
        self.assertEqual(self.calls, [])

    def test_repository_target_and_symlinked_signature_file_are_rejected(self):
        with tempfile.TemporaryDirectory(dir=signing.ROOT) as local:
            local_session = Path(local) / "session"
            shutil.copytree(self.session, local_session)
            with self.assertRaisesRegex(HarnessError, "outside the repository"):
                signing.signing_proposal(local_session)
        seal = self.app / "Contents/_CodeSignature/CodeResources"
        seal.unlink()
        seal.symlink_to(self.source / "Contents" / signing.EXECUTABLE)
        with self.assertRaisesRegex(HarnessError, "escapes disposable copy"):
            signing.signing_proposal(self.session)
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
