"""Synthetic-only checks for the main-account metadata inspector."""

import contextlib
import hashlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from harness import game_launch, main_account


class MainAccountReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.app = self.root / "synthetic.app"
        self.data = self.root / "synthetic-data"
        release = self.app / main_account.RELEASE_RELATIVE
        assembly = self.app / game_launch.ASSEMBLY
        release.parent.mkdir(parents=True)
        assembly.parent.mkdir(parents=True)
        release.write_text(json.dumps({"version": game_launch.VERSION, "commit": game_launch.COMMIT}))
        self.assembly_bytes = b"synthetic assembly fixture"
        assembly.write_bytes(self.assembly_bytes)
        self.hash_patch = mock.patch.object(game_launch, "ASSEMBLY_HASH",
                                      hashlib.sha256(self.assembly_bytes).hexdigest())
        self.hash_patch.start()
        self.addCleanup(self.hash_patch.stop)
        self.uid = os.getuid()

    def inspect(self):
        return main_account.inspect_readiness(self.app, self.data, self.uid)

    def test_matching_build_and_bounded_metadata_do_not_enable_main_play(self):
        secret_id = "12345678901234567"
        secret_local = "private-local-player-name"
        steam_user = self.data / "steam" / secret_id
        local_user = self.data / "default" / secret_local
        (steam_user / "profile0").mkdir(parents=True)
        (steam_user / "modded" / "profile2").mkdir(parents=True)
        (local_user / "profile1").mkdir(parents=True)
        private_save = steam_user / "profile0" / "private-save.secret"
        private_save.write_text("sensitive fixture contents")
        before = private_save.read_bytes()
        result = self.inspect()
        self.assertEqual(result["game_build"], "MATCH")
        self.assertEqual(result["steam_namespace"], "SINGLE")
        self.assertEqual(result["steam_data"]["user_directories"], 1)
        self.assertEqual(result["steam_data"]["profile_directories"], 1)
        self.assertEqual(result["steam_data"]["modded_profile_directories"], 1)
        self.assertEqual(result["local_data"]["user_directories"], 1)
        self.assertEqual(result["local_data"]["profile_directories"], 1)
        self.assertEqual(result["steam_cloud_state"], "UNVERIFIED")
        self.assertFalse(result["main_launch_enabled"])
        for flag in ("save_contents_read", "network_requests_made", "files_written",
                     "signing_performed", "credentials_persisted"):
            self.assertFalse(result[flag])
        exported = json.dumps(result)
        for private in (secret_id, secret_local, "private-save", "sensitive fixture", str(self.root)):
            self.assertNotIn(private, exported)
        self.assertEqual(private_save.read_bytes(), before)

    def test_only_vendor_files_are_opened_as_regular_files(self):
        save = self.data / "steam" / "123" / "profile0" / "save.secret"
        save.parent.mkdir(parents=True)
        save.write_bytes(b"private")
        original_open = main_account.os.open
        opened = []

        def checked_open(path, flags, *args, **kwargs):
            if not flags & os.O_DIRECTORY:
                opened.append(str(path))
                self.assertIn(str(path), {"release_info.json", "sts2.dll"})
            return original_open(path, flags, *args, **kwargs)

        with mock.patch.object(main_account.os, "open", side_effect=checked_open):
            result = self.inspect()
        self.assertEqual(result["game_build"], "MATCH")
        self.assertEqual(set(opened), {"release_info.json", "sts2.dll"})
        self.assertEqual(save.read_bytes(), b"private")

    def test_mismatched_and_linked_vendor_files_are_not_accepted(self):
        assembly = self.app / game_launch.ASSEMBLY
        assembly.write_bytes(b"different")
        self.assertEqual(self.inspect()["game_build"], "MISMATCH")
        assembly.unlink()
        target = self.root / "outside"
        target.write_bytes(self.assembly_bytes)
        assembly.symlink_to(target)
        self.assertEqual(self.inspect()["game_build"], "UNREADABLE")

    def test_vendor_fifo_and_linked_ancestor_cannot_be_read(self):
        assembly = self.app / game_launch.ASSEMBLY
        assembly.unlink()
        os.mkfifo(assembly)
        self.assertEqual(self.inspect()["game_build"], "UNREADABLE")
        assembly.unlink()
        assembly.write_bytes(self.assembly_bytes)
        linked_parent = self.root / "linked-parent"
        linked_parent.symlink_to(self.app, target_is_directory=True)
        self.assertEqual(main_account.inspect_readiness(linked_parent, self.data, self.uid)
                         ["game_build"], "REDIRECTED")

    def test_redirected_data_is_not_followed(self):
        outside = self.root / "outside-data"
        (outside / "steam" / "123" / "profile0").mkdir(parents=True)
        self.data.symlink_to(outside, target_is_directory=True)
        result = self.inspect()
        self.assertEqual(result["data_root"], "REDIRECTED")
        self.assertEqual(result["steam_data"]["status"], "NOT_INSPECTED")
        self.assertEqual(result["steam_namespace"], "UNVERIFIED")
        self.data.unlink()
        self.data.mkdir()
        (self.data / "steam").symlink_to(outside / "steam", target_is_directory=True)
        result = self.inspect()
        self.assertEqual(result["steam_data"]["status"], "REDIRECTED")
        self.assertTrue(result["steam_data"]["inventory_incomplete"])

    def test_wrong_owner_and_ambiguous_steam_namespace(self):
        for name in ("123", "456"):
            (self.data / "steam" / name / "profile0").mkdir(parents=True)
        self.assertEqual(self.inspect()["steam_namespace"], "AMBIGUOUS")
        result = main_account.inspect_readiness(self.app, self.data, self.uid + 1)
        self.assertEqual(result["data_root"], "WRONG_OWNER")
        self.assertEqual(result["steam_namespace"], "UNVERIFIED")

    def test_nonnumeric_steam_entry_and_iteration_limit_remain_unverified(self):
        (self.data / "steam" / "unexpected-id").mkdir(parents=True)
        self.assertTrue(self.inspect()["steam_data"]["inventory_incomplete"])
        for number in range(80):
            (self.data / "steam" / str(number)).mkdir()
        result = self.inspect()
        self.assertLessEqual(result["steam_data"]["user_directories"], 64)
        self.assertTrue(result["steam_data"]["inventory_limit_reached"])
        self.assertEqual(result["steam_namespace"], "UNVERIFIED")

    def test_cli_rejects_other_account_without_exposing_paths(self):
        stderr = io.StringIO()
        with (mock.patch.object(main_account.platform, "system", return_value="Darwin"),
              mock.patch.object(main_account.os, "getuid", return_value=502),
              mock.patch.object(main_account.os, "geteuid", return_value=502),
              mock.patch.object(main_account.pwd, "getpwuid",
                                return_value=SimpleNamespace(pw_dir=str(self.root), pw_name="test")),
              mock.patch.object(main_account, "inspect_readiness", side_effect=AssertionError("called")),
              contextlib.redirect_stderr(stderr)):
            code = main_account.main(["inspect"])
        self.assertEqual(code, 2)
        self.assertEqual(stderr.getvalue().strip(), "Main-account readiness inspection stopped.")
        self.assertNotIn(str(self.root), stderr.getvalue())

    def test_missing_and_inaccessible_data_remain_unresolved(self):
        result = self.inspect()
        self.assertEqual(result["data_root"], "ABSENT")
        self.assertEqual(result["steam_data"]["status"], "ABSENT")
        self.assertEqual(result["steam_namespace"], "UNVERIFIED")
        self.data.mkdir()
        original_open = main_account.os.open

        def inaccessible(path, flags, *args, **kwargs):
            if str(path) == self.data.name:
                raise PermissionError("private-path-and-account-detail")
            return original_open(path, flags, *args, **kwargs)

        with mock.patch.object(main_account.os, "open", side_effect=inaccessible):
            result = self.inspect()
        self.assertEqual(result["data_root"], "INACCESSIBLE")
        self.assertEqual(result["steam_data"]["status"], "NOT_INSPECTED")
        self.assertNotIn("private-path-and-account-detail", json.dumps(result))

    def test_total_scan_budget_cannot_certify_a_partial_inventory(self):
        for user in range(20):
            for profile in range(30):
                (self.data / "steam" / str(user) / f"profile{profile}").mkdir(parents=True)
        (self.data / "default" / "private-local-id" / "profile1").mkdir(parents=True)
        result = self.inspect()
        counted = sum(result[key][field] for key in ("steam_data", "local_data")
                      for field in ("user_directories", "profile_directories", "modded_profile_directories"))
        self.assertLessEqual(counted, main_account.LIMIT_TOTAL)
        self.assertTrue(result["steam_data"]["inventory_limit_reached"])
        self.assertTrue(result["local_data"]["inventory_incomplete"])
        self.assertEqual(result["steam_namespace"], "UNVERIFIED")

    def test_inspection_does_not_invoke_network_process_or_mutation_interfaces(self):
        (self.data / "steam" / "123" / "profile1").mkdir(parents=True)
        forbidden = AssertionError("inspection attempted an active operation")
        with (mock.patch("subprocess.run", side_effect=forbidden),
              mock.patch("subprocess.Popen", side_effect=forbidden),
              mock.patch("socket.create_connection", side_effect=forbidden),
              mock.patch("socket.socket", side_effect=forbidden),
              mock.patch("os.system", side_effect=forbidden),
              mock.patch("os.chmod", side_effect=forbidden),
              mock.patch("os.replace", side_effect=forbidden),
              mock.patch("os.unlink", side_effect=forbidden)):
            result = self.inspect()
        self.assertEqual(result["game_build"], "MATCH")
        self.assertFalse(result["main_launch_enabled"])


if __name__ == "__main__":
    unittest.main()
