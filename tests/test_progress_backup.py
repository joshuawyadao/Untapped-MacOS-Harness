"""Synthetic progress backup safety checks; no real game data is used."""

import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock

from harness.asar import HarnessError
from harness import progress_backup as backup


class ProgressBackupTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.source = self.root / "original"
        self.source.mkdir(mode=0o700)
        (self.source / "slot").mkdir(mode=0o700)
        (self.source / "empty").mkdir(mode=0o700)
        (self.source / "slot" / "save.dat").write_bytes(b"original progress\x00\xff")
        (self.source / "settings.cfg").write_text("windowed=true\n")
        parent = self.root / "backups"
        parent.mkdir(mode=0o700)
        self.dest = parent / "snapshot"

    def snapshot(self):
        return {str(p.relative_to(self.source)): p.read_bytes()
                for p in self.source.rglob("*") if p.is_file() and not p.is_symlink()}

    def test_private_roundtrip_preserves_original_and_empty_directories(self):
        before = self.snapshot()
        result = backup.create_backup(self.source, self.dest)
        self.assertEqual(result, {"files": 2, "bytes": sum(map(len, before.values())), "verified": True})
        self.assertEqual(backup.verify_backup(self.dest), result)
        self.assertIsNone(backup.assert_source_unchanged(self.source, self.dest))
        self.assertEqual(self.snapshot(), before)
        self.assertTrue((self.dest / "payload" / "empty").is_dir())
        self.assertEqual(stat.S_IMODE(self.dest.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((self.dest / "payload" / "slot" / "save.dat").stat().st_mode), 0o600)
        receipt = self.dest / "receipt.json"
        self.assertEqual(stat.S_IMODE(receipt.stat().st_mode), 0o600)
        self.assertNotIn(str(self.source).encode(), receipt.read_bytes())
        self.assertEqual(set(result), {"files", "bytes", "verified"})

    def test_verification_rejects_tampering(self):
        for tamper in ("content", "extra", "missing", "mode", "receipt"):
            with self.subTest(tamper=tamper):
                target = self.dest.parent / tamper
                backup.create_backup(self.source, target)
                file = target / "payload" / "slot" / "save.dat"
                if tamper == "content":
                    file.write_bytes(b"changed")
                elif tamper == "extra":
                    (target / "payload" / "new").write_bytes(b"extra")
                elif tamper == "missing":
                    file.unlink()
                elif tamper == "mode":
                    file.chmod(0o644)
                else:
                    data = json.loads((target / "receipt.json").read_text())
                    data["records"]["slot/save.dat"]["sha256"] = "0" * 64
                    (target / "receipt.json").write_text(json.dumps(data))
                with self.assertRaises(HarnessError):
                    backup.verify_backup(target)

    def test_verification_rejects_payload_links(self):
        for kind in ("symlink", "hardlink"):
            with self.subTest(kind=kind):
                target = self.dest.parent / f"payload-{kind}"
                backup.create_backup(self.source, target)
                file = target / "payload" / "slot" / "save.dat"
                if kind == "symlink":
                    file.unlink()
                    file.symlink_to(self.source / "slot" / "save.dat")
                else:
                    os.link(file, target / "payload" / "slot" / "other.dat")
                with self.assertRaises(HarnessError):
                    backup.verify_backup(target)

    def test_source_change_detected_without_writing_to_it(self):
        backup.create_backup(self.source, self.dest)
        (self.source / "slot" / "save.dat").write_bytes(b"new progress")
        changed = self.snapshot()
        with self.assertRaises(HarnessError):
            backup.assert_source_unchanged(self.source, self.dest)
        self.assertEqual(self.snapshot(), changed)
        self.assertTrue(backup.verify_backup(self.dest)["verified"])

    def test_empty_tree_and_source_metadata_change(self):
        empty = self.root / "empty-original"
        empty.mkdir(mode=0o700)
        target = self.dest.parent / "empty-snapshot"
        self.assertEqual(backup.create_backup(empty, target),
                         {"files": 0, "bytes": 0, "verified": True})
        self.assertEqual(backup.verify_backup(target)["files"], 0)
        empty.chmod(0o750)
        with self.assertRaises(HarnessError):
            backup.assert_source_unchanged(empty, target)

    def test_unsafe_entries_have_no_success_receipt(self):
        for kind in ("symlink_file", "symlink_dir", "hardlink", "fifo"):
            with self.subTest(kind=kind):
                target = self.dest.parent / kind
                entry = self.source / "unsafe"
                if kind == "symlink_file":
                    entry.symlink_to(self.source / "settings.cfg")
                elif kind == "symlink_dir":
                    entry.symlink_to(self.source / "slot", target_is_directory=True)
                elif kind == "hardlink":
                    os.link(self.source / "settings.cfg", entry)
                else:
                    os.mkfifo(entry)
                before = self.snapshot()
                try:
                    with self.assertRaises(HarnessError) as raised:
                        backup.create_backup(self.source, target)
                    self.assertNotIn(str(self.source), str(raised.exception))
                    self.assertFalse((target / "receipt.json").exists())
                    self.assertEqual(self.snapshot(), before)
                finally:
                    entry.unlink()

    def test_rejects_overlap_existing_destination_and_ancestor_link(self):
        with self.assertRaises(HarnessError):
            backup.create_backup(self.source, self.source / "inside")
        self.assertFalse((self.source / "inside").exists())
        self.dest.mkdir()
        with self.assertRaises(HarnessError):
            backup.create_backup(self.source, self.dest)
        link = self.root / "alias"
        link.symlink_to(self.source, target_is_directory=True)
        with self.assertRaises(HarnessError):
            backup.create_backup(link, self.dest.parent / "other")

    def test_bounds_and_copy_race_leave_no_receipt(self):
        with mock.patch.object(backup, "MAX_BYTES", 2):
            with self.assertRaises(HarnessError):
                backup.create_backup(self.source, self.dest)
        self.assertFalse((self.dest / "receipt.json").exists())

        target = self.dest.parent / "raced"
        original_walk = backup._walk
        calls = 0

        def racing_walk(*args, **kwargs):
            nonlocal calls
            result = original_walk(*args, **kwargs)
            calls += 1
            if calls == 2:
                (self.source / "slot" / "save.dat").write_bytes(b"changed during copy")
            return result

        with mock.patch.object(backup, "_walk", racing_walk):
            with self.assertRaises(HarnessError):
                backup.create_backup(self.source, target)
        self.assertFalse((target / "receipt.json").exists())

    def test_file_count_and_depth_bounds(self):
        with mock.patch.object(backup, "MAX_FILES", 1):
            with self.assertRaises(HarnessError):
                backup.create_backup(self.source, self.dest)
        self.assertFalse((self.dest / "receipt.json").exists())
        deep = self.source
        for index in range(backup.MAX_DEPTH + 1):
            deep = deep / f"d{index}"
            deep.mkdir(mode=0o700)
        with self.assertRaises(HarnessError):
            backup.create_backup(self.source, self.dest.parent / "deep")


if __name__ == "__main__":
    unittest.main()
