"""Private saved-error classification must never export arbitrary input."""

import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from harness import auth_diagnostic as auth
from harness.asar import HarnessError


class AuthDiagnosticTests(unittest.TestCase):
    def test_challenge_classification_excludes_every_secret_and_url(self):
        raw = ('[AuthorizationWorkflow] Failed to exchange token or complete authorization: '
               + auth.TOKEN_ERROR + ' <!DOCTYPE html><html><title>Just a moment</title>'
               '<script src="/cdn-cgi/challenge-platform/private"></script>Cloudflare '
               'token=secret-value person@example.test https://private.example/callback?code=secret</html>')
        result = auth.classify([raw])
        self.assertEqual(result['classification'], 'UPSTREAM_SECURITY_PAGE')
        self.assertTrue(result['callback_failure_logged'])
        self.assertTrue(result['html_marker'])
        self.assertTrue(result['cloudflare_marker'])
        self.assertEqual(result['oauth_error_codes'], [])
        serialized = json.dumps(result)
        for secret in ('secret-value', 'person@', 'https://', 'private.example', '<html>'):
            self.assertNotIn(secret, serialized)

    def test_only_known_json_oauth_errors_are_exported(self):
        for code in auth.OAUTH_ERRORS:
            result = auth.classify([auth.TOKEN_ERROR + json.dumps({'error':code, 'error_description':'secret'})])
            self.assertEqual(result['classification'], 'OAUTH_PROTOCOL_ERROR')
            self.assertEqual(result['oauth_error_codes'], [code])
            self.assertNotIn('secret', json.dumps(result))
        result = auth.classify([auth.TOKEN_ERROR + '{"error":"private-account@example.test"}'])
        self.assertEqual(result['classification'], 'UNCLASSIFIED_TOKEN_ERROR')
        self.assertEqual(result['oauth_error_codes'], [])

    def test_unrelated_html_and_later_log_lines_are_not_token_evidence(self):
        result = auth.classify(['<html>Just a moment</html>\n[AuthorizationWorkflow] Completed token exchange'])
        self.assertEqual(result['classification'], 'NO_TOKEN_ERROR_BODY')
        self.assertFalse(result['html_marker'])
        self.assertTrue(result['token_exchange_completed_logged'])
        result = auth.classify([auth.TOKEN_ERROR + 'Forbidden\n[2026-11-03 20:20:20] unrelated <html>Just a moment</html>'])
        self.assertEqual(result['classification'], 'UNCLASSIFIED_TOKEN_ERROR')
        self.assertFalse(result['browser_challenge_marker'])

    def test_owned_reader_is_bounded_and_refuses_links_and_special_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / 'private.log'
            path.write_bytes(b'secret-prefix' + b'x' * 100)
            text, limited = auth._read_owned(path, 20, tail=True)
            self.assertTrue(limited)
            self.assertEqual(text, 'x' * 20)
            with self.assertRaises(HarnessError): auth._read_owned(path, 20)
            with patch.object(auth.os, 'getuid', return_value=os.getuid() + 1):
                with self.assertRaises(HarnessError): auth._read_owned(path, 20)
            link = root / 'link'; link.symlink_to(path)
            with self.assertRaises(HarnessError): auth._read_owned(link, 20)
            hard = root / 'hard'; os.link(path, hard)
            with self.assertRaises(HarnessError): auth._read_owned(path, 20)
            fifo = root / 'fifo'; os.mkfifo(fifo)
            with self.assertRaises(HarnessError): auth._read_owned(fifo, 20)

    def attempt(self, home):
        session = home / 'session'; session.mkdir(mode=0o700)
        attempt = session / 'outer-attempt-1234abcd'; attempt.mkdir(mode=0o700)
        (attempt / 'profile').mkdir(mode=0o700)
        (attempt / 'manifest.json').write_text(json.dumps({'controlled_access_version':1, 'prepared_session':str(session)}))
        (attempt / 'launch.json').write_text(json.dumps({'manual_oauth':True,'outer_sandbox_retained':True}))
        return attempt

    def test_inspection_reads_only_two_logs_and_preserves_private_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp).resolve(); attempt = self.attempt(home)
            log = attempt / 'profile/log.log'
            log.write_text(auth.TOKEN_ERROR + '<html>Forbidden</html> secret-token')
            (attempt / 'profile/manual-sign-in-url.txt').write_text('must-never-be-read')
            before = {p: p.read_bytes() for p in attempt.rglob('*') if p.is_file()}
            result = auth.inspect_attempt(attempt, home)
            self.assertEqual(result['classification'], 'UPSTREAM_HTML_ERROR')
            self.assertEqual(result['log_files_checked'], 1)
            self.assertFalse(result['network_requests_made'])
            self.assertNotIn('secret-token', json.dumps(result))
            self.assertEqual(before, {p: p.read_bytes() for p in attempt.rglob('*') if p.is_file()})
            (attempt / 'launch.json').write_text('{"manual_oauth":false,"outer_sandbox_retained":true}')
            with self.assertRaises(HarnessError): auth.inspect_attempt(attempt, home)

    def test_redirected_and_shared_attempt_directories_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp).resolve(); attempt = self.attempt(home)
            alias = attempt.parent / 'outer-attempt-5678efgh'; alias.symlink_to(attempt)
            with self.assertRaises(HarnessError): auth.inspect_attempt(alias, home)
            (attempt / 'profile').chmod(0o755)
            with self.assertRaises(HarnessError): auth.inspect_attempt(attempt, home)

    def test_cli_export_and_errors_are_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp).resolve(); attempt = self.attempt(home)
            (attempt / 'stdout.log').write_text(auth.TOKEN_ERROR + '{"error":"invalid_grant","token":"secret-token"}')
            with patch.object(auth.game_launch, 'test_identity', return_value=(os.getuid(),home,None)), contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(auth.main([str(attempt)]), 0)
            file = Path(output.getvalue().splitlines()[0].removeprefix('Diagnostic file: '))
            try:
                self.assertEqual(file.stat().st_mode & 0o777, 0o644)
                self.assertNotIn('secret-token', file.read_text())
                self.assertEqual(json.loads(file.read_text())['oauth_error_codes'], ['invalid_grant'])
            finally:
                file.unlink()
        with patch.object(auth, 'run', side_effect=HarnessError('token=secret-token')), contextlib.redirect_stderr(io.StringIO()) as error:
            self.assertEqual(auth.main(['/unused']), 2)
        self.assertNotIn('secret-token', error.getvalue())


if __name__ == '__main__':
    unittest.main()
