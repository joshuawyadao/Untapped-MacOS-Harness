"""Private identity-helper construction and own-process native checks."""

import hashlib
import os
import platform
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from harness.asar import HarnessError
from harness import process_identity as identity


class IdentityPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.profile = Path(self.temp.name).resolve() / "profile"
        self.profile.mkdir(mode=0o700)
        self.darwin = mock.patch.object(identity.platform, "system", return_value="Darwin")
        self.darwin.start()
        self.addCleanup(self.darwin.stop)

    def _compiler(self, command, **options):
        output = Path(command[-1])
        output.write_bytes(b"synthetic executable")
        self.assertEqual(command[:5], ["/usr/bin/clang", "-Wall", "-Wextra", "-Werror", "-Os"])
        self.assertEqual(command[-2], "-o")
        self.assertEqual(Path(command[5]).name, "target_identity.c")
        self.assertEqual(options["timeout"], 30)
        self.assertEqual(options["env"].keys(), {"PATH", "LANG", "TMPDIR"})
        self.assertEqual(options["env"]["PATH"], "/usr/bin:/bin")
        self.assertEqual(options["cwd"], options["env"]["TMPDIR"])
        return SimpleNamespace(returncode=0, stderr=b"")

    def test_compiles_with_clean_environment_and_installs_private_helper(self):
        with mock.patch.dict(os.environ, {"CPATH": "/untrusted", "SDKROOT": "/untrusted",
                                         "DYLD_INSERT_LIBRARIES": "/untrusted",
                                         "SteamAppId": "untrusted"}), \
                mock.patch.object(identity.subprocess, "run", side_effect=self._compiler) as compiler:
            result = identity.prepare_identity_probe(self.profile)
        destination = self.profile / "target-identity"
        self.assertEqual(result, {"path": str(destination),
                                  "sha256": hashlib.sha256(b"synthetic executable").hexdigest()})
        self.assertEqual(destination.read_bytes(), b"synthetic executable")
        self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o700)
        self.assertEqual(destination.stat().st_nlink, 1)
        self.assertEqual(destination.stat().st_uid, os.getuid())
        self.assertEqual(list(self.profile.iterdir()), [destination])
        compiler.assert_called_once()
        with self.assertRaisesRegex(HarnessError, "already exists"):
            identity.prepare_identity_probe(self.profile)

    def test_rejects_failure_timeout_and_missing_or_unsafe_output(self):
        cases = [
            (lambda command, **kwargs: SimpleNamespace(returncode=1, stderr=b"compile error"), "compilation failed"),
            (lambda command, **kwargs: SimpleNamespace(returncode=0, stderr=b""), "did not create"),
            (lambda command, **kwargs: (_ for _ in ()).throw(subprocess.TimeoutExpired(command, 30)), "timed out"),
        ]
        for compiler, message in cases:
            with self.subTest(message=message), mock.patch.object(identity.subprocess, "run", side_effect=compiler):
                with self.assertRaisesRegex(HarnessError, message):
                    identity.prepare_identity_probe(self.profile)
                self.assertEqual(list(self.profile.iterdir()), [])
        def symlink_output(command, **kwargs):
            Path(command[-1]).symlink_to(self.profile)
            return SimpleNamespace(returncode=0, stderr=b"")
        with mock.patch.object(identity.subprocess, "run", side_effect=symlink_output):
            with self.assertRaisesRegex(HarnessError, "unsafe"):
                identity.prepare_identity_probe(self.profile)
        self.assertEqual(list(self.profile.iterdir()), [])

    def test_rejects_noncanonical_or_unsafe_profile_before_compiling(self):
        aliases = self.profile.parent / "alias"
        aliases.symlink_to(self.profile, target_is_directory=True)
        with mock.patch.object(identity.subprocess, "run") as compiler:
            for path in (aliases, self.profile / ".." / "profile", self.profile.parent / "absent"):
                with self.subTest(path=path), self.assertRaises(HarnessError):
                    identity.prepare_identity_probe(path)
            self.profile.chmod(0o755)
            with self.assertRaisesRegex(HarnessError, "mode 0700"):
                identity.prepare_identity_probe(self.profile)
            self.profile.chmod(0o700)
            other_uid = os.getuid() + 1
            with mock.patch.object(identity.os, "getuid", return_value=other_uid), \
                    mock.patch.object(identity.os, "geteuid", return_value=other_uid):
                with self.assertRaisesRegex(HarnessError, "owned"):
                    identity.prepare_identity_probe(self.profile)
            compiler.assert_not_called()

    def test_rejects_existing_symlink_destination_and_non_mac(self):
        destination = self.profile / "target-identity"
        destination.symlink_to(self.profile.parent / "missing")
        with mock.patch.object(identity.subprocess, "run") as compiler:
            with self.assertRaisesRegex(HarnessError, "already exists"):
                identity.prepare_identity_probe(self.profile)
            compiler.assert_not_called()
        with mock.patch.object(identity.platform, "system", return_value="Linux"):
            with self.assertRaisesRegex(HarnessError, "macOS"):
                identity.prepare_identity_probe(self.profile)


@unittest.skipUnless(platform.system() == "Darwin" and Path("/usr/bin/clang").is_file(),
                     "requires macOS and clang")
class NativeIdentityTests(unittest.TestCase):
    def test_own_process_path_and_invalid_pid_rejection(self):
        if os.getuid() == 0:
            self.skipTest("helper refuses privileged execution")
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary).resolve() / "profile"
            profile.mkdir(mode=0o700)
            report = identity.prepare_identity_probe(profile)
            helper = report["path"]
            own = subprocess.run([helper, str(os.getpid())], capture_output=True,
                                 text=True, check=True, timeout=5)
            uid, path = own.stdout.rstrip("\n").split(" ", 1)
            self.assertEqual(uid, str(os.getuid()))
            self.assertEqual(own.stdout, f"{uid} {path}\n")
            self.assertTrue(Path(path).is_absolute())
            self.assertTrue(Path(path).is_file())
            self.assertTrue(os.access(path, os.X_OK))
            self.assertEqual(own.stderr, "")
            for bad in ("0", "01", "+1", "-1", "1 ", "1\n", "2147483648", "abc"):
                with self.subTest(bad=repr(bad)):
                    result = subprocess.run([helper, bad], capture_output=True,
                                            text=True, timeout=5)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(result.stdout, "")
            missing = subprocess.run([helper, str(2**31 - 1)], capture_output=True,
                                     text=True, timeout=5)
            self.assertNotEqual(missing.returncode, 0)
            self.assertEqual(missing.stdout, "")


if __name__ == "__main__":
    unittest.main()
