"""Target preflight must reject wrong processes before any app is launched."""
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from harness import cli
from harness.asar import HarnessError

class TargetLaunchTests(unittest.TestCase):
    def test_partial_or_invalid_target_refuses_before_validation(self):
        for pid, game in ((None, '/tmp/game'), (12, None), (0, '/tmp/game')):
            with self.subTest(pid=pid), patch.object(cli, '_validate_launch_copy') as validate:
                with self.assertRaises(HarnessError):
                    cli.launch_outer(Path('/tmp/session'), 45, True, pid, game)
                validate.assert_not_called()

    def test_wrong_uid_or_executable_refuses_before_validation(self):
        with tempfile.TemporaryDirectory() as d:
            game = Path(d).resolve()/'game'
            game.touch()
            for row in (f'{os.getuid()+1} {game}', f'{os.getuid()} /wrong/game'):
                with self.subTest(row=row), patch.object(cli.subprocess, 'run', return_value=SimpleNamespace(stdout=row)), patch.object(cli, '_validate_launch_copy') as validate:
                    with self.assertRaises(HarnessError):
                        cli.launch_outer(Path('/tmp/session'), 45, True, 123, game)
                    validate.assert_not_called()

    def test_verified_target_reaches_signed_copy_validation(self):
        with tempfile.TemporaryDirectory() as d:
            game = Path(d).resolve()/'game with spaces'
            game.touch()
            with patch.object(cli.subprocess, 'run', return_value=SimpleNamespace(stdout=f'{os.getuid()} {game}\n')), patch.object(cli, '_validate_launch_copy', side_effect=HarnessError('signed validation reached')):
                with self.assertRaisesRegex(HarnessError, 'signed validation reached'):
                    cli.launch_outer(Path('/tmp/session'), 45, True, 123, game)
