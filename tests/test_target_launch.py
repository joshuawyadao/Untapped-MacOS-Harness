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

    def test_targeted_launch_supplies_only_fresh_probe_hash_and_stops_on_build_failure(self):
        from unittest import mock
        import subprocess
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            app = root / 'Companion.app'
            app.mkdir()
            (root / 'signing.json').write_text('{}')
            game = root / 'game executable'
            game.touch()
            process = mock.Mock(pid=43210)
            process.wait.side_effect = subprocess.TimeoutExpired('synthetic', 1)
            for failure in (False, True):
                def build(profile):
                    self.assertTrue(profile.is_dir())
                    if failure:
                        raise HarnessError('compiler unavailable')
                    return {'path': str(profile / 'target-identity'), 'sha256': 'a' * 64}
                with self.subTest(failure=failure), \
                        mock.patch.object(cli, '_validate_launch_copy', return_value=(root, {}, app)), \
                        mock.patch.object(cli.subprocess, 'run', return_value=SimpleNamespace(stdout=f'{os.getuid()} {game}')), \
                        mock.patch.object(cli, 'prepare_identity_probe', side_effect=build) as prepare, \
                        mock.patch.object(cli.subprocess, 'Popen', return_value=process) as spawn, \
                        mock.patch.object(cli, 'stop_probe') as stop:
                    if failure:
                        with self.assertRaisesRegex(HarnessError, 'compiler unavailable'):
                            cli.launch_outer(root, 1, True, 123, game)
                        spawn.assert_not_called()
                    else:
                        result = cli.launch_outer(root, 1, True, 123, game)
                        self.assertEqual(spawn.call_args.kwargs['env']['UNTAPPED_HARNESS_IDENTITY_SHA256'], 'a' * 64)
                        self.assertEqual(spawn.call_args.kwargs['env']['UC_TEST_SANDBOX_DIR'], str(Path(result['attempt_dir'])/'profile'))
                        stop.assert_called_once_with(process)
                    prepare.assert_called_once()
