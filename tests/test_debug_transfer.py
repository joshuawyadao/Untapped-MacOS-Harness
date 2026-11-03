"""Real inert archive extraction regression; never runs or signs a game."""
import os
import stat
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from harness import game_debug
from harness.asar import HarnessError


@unittest.skipIf(os.getuid() == 0, 'private transfer intentionally refuses root')
class DebugTransferTests(unittest.TestCase):
    def test_private_umask_keeps_recorded_file_modes_and_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            source = root/'source';source.mkdir()
            for name, mode in (('executable', 0o755), ('resource', 0o644)):
                path=source/name;path.write_bytes(b'original inert fixture');path.chmod(mode)
            archive=root/'inert.tar'
            with tarfile.open(archive,'w') as stream:
                for path in source.iterdir(): stream.add(path,arcname=path.name)
            destination=root/'extract';destination.mkdir(mode=0o700)
            previous=os.umask(0o077)
            try:
                with patch.object(game_debug.platform,'system',return_value='Darwin'):
                    game_debug.extract_transfer(archive,destination)
            finally:
                os.umask(previous)
            self.assertEqual(stat.S_IMODE(destination.stat().st_mode),0o700)
            for path in source.iterdir():
                copy=destination/path.name
                self.assertEqual(copy.read_bytes(),path.read_bytes())
                self.assertEqual(stat.S_IMODE(copy.stat().st_mode),stat.S_IMODE(path.stat().st_mode))

    def test_refuses_nonempty_or_redirected_destination_before_tar(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();archive=root/'a.tar';archive.touch()
            destination=root/'extract';destination.mkdir(mode=0o700)
            (destination/'keep').write_text('existing data')
            link=root/'redirect';link.symlink_to(destination)
            with patch.object(game_debug.platform,'system',return_value='Darwin'), patch.object(game_debug.subprocess,'run') as run:
                for path in (destination,link):
                    with self.subTest(path=path),self.assertRaises(HarnessError):
                        game_debug.extract_transfer(archive,path)
                run.assert_not_called()
            self.assertEqual((destination/'keep').read_text(),'existing data')

    def test_tar_failure_stops_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();archive=root/'bad.tar';archive.write_text('not an archive')
            destination=root/'extract';destination.mkdir(mode=0o700)
            with patch.object(game_debug.platform,'system',return_value='Darwin'):
                with self.assertRaisesRegex(HarnessError,'extraction failed'):
                    game_debug.extract_transfer(archive,destination)
