"""Native-worker protocol and sign-in boundary checks, without apps or network."""
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import urlencode
from harness import desktop_launcher as desktop
from harness.asar import HarnessError


def valid_url(**changes):
    fields = dict(response_type='code', scope='companion:full-access', code_challenge_method='S256',
                  utm_source='uc', utm_medium='app', utm_campaign='accounts', utm_content='add-account-button',
                  client_id='public-client', state='private-state', code_challenge='challenge',
                  redirect_uri='http://localhost:17791/')
    fields.update(changes)
    return 'https://accounts.untapped.gg/authorize?' + urlencode(fields)


class DesktopTests(unittest.TestCase):
    def test_login_accepts_only_the_reviewed_account_flow(self):
        self.assertEqual(desktop.oauth_url(valid_url()), valid_url())
        for value in (valid_url()+'&state=duplicate', valid_url().replace('accounts.untapped.gg', 'evil.example'),
                      valid_url(redirect_uri='https://evil.example/'), valid_url(scope='other'),
                      valid_url(extra='value'), valid_url()+'#fragment', valid_url(franchise='OTHER')):
            with self.subTest(url=value), self.assertRaises((HarnessError, ValueError)):
                desktop.oauth_url(value)

    def test_signin_file_rejects_symlinks_and_unsafe_modes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            root.chmod(0o700)
            f = root / 'manual-sign-in-url.txt'
            f.write_text(valid_url());f.chmod(0o600)
            self.assertEqual(desktop.read_signin(root), valid_url())
            f.chmod(0o644)
            with self.assertRaises(HarnessError):desktop.read_signin(root)
            f.unlink();f.symlink_to(root / 'other')
            with self.assertRaises(OSError):desktop.read_signin(root)

    def test_exclusive_lock_releases_without_removing_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with desktop.session_lock(root):
                with self.assertRaises(HarnessError):
                    with desktop.session_lock(root):pass
            with desktop.session_lock(root):pass

    def test_eof_invalid_and_stop_commands_cancel(self):
        for value in ('', '{bad}\n', '{"action":"stop"}\n', '{"action":"launch_other"}\n', 'x'*1025):
            controls = desktop.Controls(io.StringIO())
            controls.commands(io.StringIO(value))
            self.assertTrue(controls.stop.is_set())

    def test_only_explicit_signin_opens_validated_url_and_keeps_it_out_of_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();root.chmod(0o700)
            f=root/'manual-sign-in-url.txt';f.write_text(valid_url());f.chmod(0o600)
            out=io.StringIO();controls=desktop.Controls(out);controls.profile=root
            with patch.object(desktop.subprocess,'run') as opened:
                controls.commands(io.StringIO('{"action":"steam_ready"}\n'))
                opened.assert_not_called()
                controls.stop.clear()
                controls.commands(io.StringIO('{"action":"sign_in"}\n'))
                self.assertEqual(opened.call_args.args[0], ['/usr/bin/open',valid_url()])
            self.assertNotIn('private-state',out.getvalue())

    def test_worker_uses_game_lifetime_callbacks_and_fixed_messages(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'runs').mkdir()
            out=io.StringIO()
            def start(**kwargs):
                self.assertIsNone(kwargs['seconds'])
                self.assertIsNone(kwargs['remember_store'])
                self.assertTrue(kwargs['approved'] and kwargs['cloud_confirmed'] and kwargs['account_confirmed'])
                self.assertTrue(callable(kwargs['should_stop']))
                kwargs['on_companion_ready'](root)
                return {'game_exit_code':0,'companion':{'reason':'GAME_EXIT','failure_stage':'NONE',
                        'gateway_cleanup_complete':True,'companion_group_cleanup_complete':True}}
            with patch.object(desktop.main_launcher,'_prepared',return_value=(root,None,None)), \
                 patch.object(desktop.main_launcher,'start',side_effect=start):
                self.assertEqual(desktop.run_worker(io.StringIO(''),out),0)
            events=[json.loads(x) for x in out.getvalue().splitlines()]
            self.assertIn('signin_ready',[x['event'] for x in events])
            self.assertEqual(events[-1]['event'],'finished')
            self.assertNotIn(str(root),out.getvalue())

    def test_steam_confirmation_honors_cancellation(self):
        controls=desktop.Controls(io.StringIO());controls.stop.set()
        with patch.object(desktop.subprocess,'run') as opened:
            with self.assertRaises(KeyboardInterrupt):controls.confirm_steam()
            opened.assert_not_called()


    def test_remember_is_opt_in_and_forget_never_starts_game(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / 'runs').mkdir()
            healthy = {'game_exit_code': 0, 'companion': {'reason': 'GAME_EXIT',
                'failure_stage': 'NONE', 'gateway_cleanup_complete': True,
                'companion_group_cleanup_complete': True}}
            with patch.object(desktop.main_launcher, '_prepared', return_value=(root, None, None)), \
                 patch.object(desktop.main_launcher, 'start', return_value=healthy) as start, \
                 patch('harness.keychain_store.KeychainStore') as store:
                self.assertEqual(desktop.run_worker(io.StringIO(''), io.StringIO()), 0)
                store.assert_not_called()
                out = io.StringIO()
                self.assertEqual(desktop.run_worker(io.StringIO(''), out, remember=True,
                    keychain_helper=Path('/private/fake'), keychain_sha256='a'*64), 0)
                self.assertIs(start.call_args.kwargs['remember_store'], store.return_value)
                start.reset_mock()
                self.assertEqual(desktop.run_worker(io.StringIO(''), out, forget=True,
                    keychain_helper=Path('/private/fake'), keychain_sha256='a'*64), 0)
                store.return_value.clear.assert_called_once_with()
                start.assert_not_called()
                self.assertEqual(json.loads(out.getvalue().splitlines()[-1])['event'], 'finished')
                store.return_value.clear.side_effect = HarnessError('private-token')
                out = io.StringIO()
                self.assertEqual(desktop.run_worker(io.StringIO(''), out, forget=True,
                    keychain_helper=Path('/private/fake'), keychain_sha256='a'*64), 1)
                self.assertEqual(json.loads(out.getvalue().splitlines()[-1])['event'], 'error')
                self.assertNotIn('private-token', out.getvalue())
                start.assert_not_called()
