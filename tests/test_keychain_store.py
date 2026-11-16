"""Keychain boundary tests; no test invokes Security.framework or a real Keychain."""

import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from harness.asar import HarnessError
from harness import keychain_store


class FakeProcess:
    def __init__(self, response):
        input_read, input_write = os.pipe()
        output_read, output_write = os.pipe()
        self.input_read = input_read
        self.stdin = os.fdopen(input_write, "wb", buffering=0)
        self.stdout = os.fdopen(output_read, "rb", buffering=0)
        os.write(output_write, response)
        os.close(output_write)
        self.returncode = 0
        self.killed = False
        self.sent = b""

    def poll(self):
        return self.returncode if self.stdout.closed else None

    def wait(self, timeout=None):
        self.returncode = 0 if not self.killed else -9
        self.sent = os.read(self.input_read, 64 * 1024 + 1)
        os.close(self.input_read)
        return self.returncode

    def kill(self):
        self.killed = True
        self.returncode = -9


class KeychainStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.helper = Path(self.temp.name).resolve() / "helper"
        self.helper.write_bytes(b"signed helper fixture")
        self.helper.chmod(0o700)
        self.digest = hashlib.sha256(self.helper.read_bytes()).hexdigest()
        self.warnings = []
        self.store = keychain_store.KeychainStore(self.helper, self.digest,
                                                   self.warnings.append)

    def _invoke(self, response, action):
        created = []
        def start_process(*args, **kwargs):
            process = FakeProcess(response)
            created.append(process)
            return process
        with mock.patch.object(keychain_store.subprocess, "run",
                               return_value=SimpleNamespace(returncode=0)) as sign, \
             mock.patch.object(keychain_store.subprocess, "Popen",
                               side_effect=start_process) as start:
            result = action()
        sign.assert_called_once_with(
            ["/usr/bin/codesign", "--verify", "--strict", str(self.helper)],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=mock.ANY, check=False,
            env={"PATH": "/usr/bin:/bin", "LANG": "C"})
        self.assertGreater(sign.call_args.kwargs["timeout"], 0)
        self.assertLessEqual(sign.call_args.kwargs["timeout"], 20)
        self.assertEqual(start.call_args.args[0][0], str(self.helper))
        self.assertEqual(start.call_args.kwargs["stderr"], subprocess.DEVNULL)
        self.assertEqual(start.call_args.kwargs["close_fds"], True)
        self.assertEqual(start.call_args.kwargs["env"],
                         {"PATH": "/usr/bin:/bin", "LANG": "C"})
        return result, start.call_args.args[0][1], created[0].sent

    def test_load_save_clear_use_fixed_operation_and_json_shapes(self):
        value = {"global": '{"accessToken":"secret-token"}'}
        loaded, operation, sent = self._invoke(json.dumps({"value": value}).encode(),
                                               self.store.load)
        self.assertEqual(operation, "load")
        self.assertEqual(json.loads(sent), {})
        self.assertEqual(loaded, value)
        _, operation, sent = self._invoke(b'{"success":true}', lambda: self.store.save(value))
        self.assertEqual(operation, "save")
        self.assertEqual(json.loads(sent), {"value": value})
        _, operation, sent = self._invoke(b'{"success":true}', self.store.clear)
        self.assertEqual(operation, "clear")
        self.assertEqual(json.loads(sent), {})
        self.assertEqual(self.warnings, [])

    def test_rejects_noncanonical_wrong_mode_and_hash_before_execution(self):
        alias = self.helper.parent / "alias"
        alias.symlink_to(self.helper)
        cases = [
            keychain_store.KeychainStore(alias, self.digest),
            keychain_store.KeychainStore(self.helper, "0" * 64),
        ]
        with mock.patch.object(keychain_store.subprocess, "run") as sign, \
             mock.patch.object(keychain_store.subprocess, "Popen") as start:
            for store in cases:
                with self.subTest(helper=store.helper), self.assertRaises(HarnessError):
                    store.load()
            self.helper.chmod(0o755)
            with self.assertRaises(HarnessError):
                self.store.load()
            sign.assert_not_called()
            start.assert_not_called()

    def test_denied_signature_or_malformed_response_is_generic(self):
        with mock.patch.object(keychain_store.subprocess, "run",
                               return_value=SimpleNamespace(returncode=1)), \
             mock.patch.object(keychain_store.subprocess, "Popen") as start:
            with self.assertRaisesRegex(HarnessError, "Remembered login is unavailable") as error:
                self.store.load()
            self.assertNotIn("secret", str(error.exception))
            start.assert_not_called()
        with self.assertRaisesRegex(HarnessError, "Remembered login is unavailable"):
            self._invoke(b'{"value":"secret-token"}', self.store.load)
        self.assertEqual(len(self.warnings), 2)
        self.assertTrue(all("secret" not in warning for warning in self.warnings))

    def test_bounded_input_and_output(self):
        with mock.patch.object(keychain_store.subprocess, "run") as sign:
            with self.assertRaises(HarnessError):
                self.store.save({"global": "x" * (64 * 1024)})
            sign.assert_not_called()
        with mock.patch.object(keychain_store, "_LIMIT", 16):
            with self.assertRaises(HarnessError):
                self._invoke(b"x" * 17, self.store.load)

    def test_launch_failure_does_not_expose_exception_text(self):
        with mock.patch.object(keychain_store.subprocess, "run",
                               return_value=SimpleNamespace(returncode=0)), \
             mock.patch.object(keychain_store.subprocess, "Popen",
                               side_effect=OSError("secret-token")):
            with self.assertRaises(HarnessError) as error:
                self.store.load()
            self.assertNotIn("secret-token", str(error.exception))

    def test_signature_and_keychain_share_one_deadline(self):
        with mock.patch.object(keychain_store.time, 'monotonic', side_effect=[0, 1, 21]), \
             mock.patch.object(keychain_store.subprocess, 'run', return_value=SimpleNamespace(returncode=0)), \
             mock.patch.object(keychain_store.subprocess, 'Popen') as start:
            with self.assertRaises(HarnessError):
                self.store.load()
            start.assert_not_called()


if __name__ == "__main__":
    unittest.main()
