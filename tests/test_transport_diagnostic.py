"""Fixed-data transport checks must keep account/error material private."""

import contextlib
import http.client
import io
import json
import os
from pathlib import Path
import socket
import ssl
import unittest
from unittest.mock import patch
from urllib.error import URLError
from urllib.parse import parse_qs

from harness import transport_diagnostic as diagnostic
from harness.asar import HarnessError


class TransportDiagnosticTests(unittest.TestCase):
    def test_exception_categories_never_copy_messages_or_nested_urls(self):
        cases = (
            (URLError(ssl.SSLCertVerificationError(1, 'secret-token private@example.test')), 'TLS_CERTIFICATE_ERROR'),
            (ssl.SSLError('secret-token'), 'TLS_PROTOCOL_ERROR'),
            (socket.gaierror(-2, 'secret-token'), 'DNS_ERROR'),
            (TimeoutError('secret-token'), 'TIMEOUT'),
            (http.client.IncompleteRead(b'secret-token', 100), 'INCOMPLETE_RESPONSE'),
            (ConnectionRefusedError(61, 'secret-token'), 'CONNECTION_REFUSED'),
            (http.client.RemoteDisconnected('secret-token'), 'CONNECTION_CLOSED'),
            (OSError(9, 'secret-token'), 'OS_ERROR'),
            (AttributeError('secret-token'), 'RESPONSE_INTERFACE_ERROR'),
            (ValueError('secret-token'), 'INTERNAL_SHAPE_ERROR'),
            (URLError('https://private.example/?token=secret-token'), 'UNKNOWN_TRANSPORT_ERROR'),
        )
        for error, category in cases:
            with self.subTest(category=category):
                result = diagnostic.exception_fields(error)
                self.assertEqual(result['transport_error'], category)
                for secret in ('secret-token', 'private@', 'https://', 'private.example'):
                    self.assertNotIn(secret, json.dumps(result))

    def test_only_fixed_reviewed_requests_and_safe_response_metadata(self):
        calls = []
        def transport(method, url, headers, body):
            calls.append((method, url, headers, body))
            return 401, {'Content-Type':'application/json; charset=utf-8', 'Set-Cookie':'secret-token'}, b'{"error":"secret-token"}'
        with patch.object(diagnostic.gateway, '_transport', side_effect=transport):
            result = diagnostic.check()
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0], ('GET','https://api.accounts.untapped.gg/api/v1/account',{},None))
        self.assertEqual(calls[1][:2], ('POST','https://api.accounts.untapped.gg/o/token'))
        form = parse_qs(calls[1][3].decode())
        self.assertEqual(form['client_id'], ['harness-inert-client'])
        self.assertEqual(form['code'], ['harness-inert-code'])
        self.assertEqual(form['code_verifier'], ['harness-inert-verifier'])
        self.assertEqual(set(form), {'client_id','code','code_verifier','grant_type','redirect_uri','scope'})
        self.assertFalse(result['real_credentials_sent'])
        self.assertNotIn('secret-token', json.dumps(result))
        self.assertEqual([x['response_kind'] for x in result['results']], ['JSON','JSON'])

    def test_first_transport_error_stops_before_second_request(self):
        with patch.object(diagnostic.gateway, '_transport', side_effect=URLError(ssl.SSLCertVerificationError(1,'secret-token'))) as transport:
            result = diagnostic.check()
        self.assertEqual(transport.call_count, 1)
        self.assertEqual(result['requests_attempted'], 1)
        self.assertEqual(result['results'][0]['transport_error'], 'TLS_CERTIFICATE_ERROR')
        self.assertNotIn('secret-token', json.dumps(result))

    def test_runtime_metadata_excludes_ca_paths_and_environment_values(self):
        with patch.dict(os.environ, {'SSL_CERT_FILE':'/private/secret-token.pem','SSL_CERT_DIR':'/private/secret-token'}):
            result = diagnostic.runtime_fields()
        self.assertTrue(result['ca_environment_overrides']['SSL_CERT_FILE'])
        self.assertTrue(result['ca_environment_overrides']['SSL_CERT_DIR'])
        self.assertNotIn('secret-token', json.dumps(result))
        self.assertTrue(all(type(x) is int for x in result['python_version']))

    def test_export_is_safe_and_identity_failure_prevents_requests(self):
        with patch.object(diagnostic.game_launch, 'test_identity'), patch.object(diagnostic.gateway,'_transport',return_value=(401,{},b'secret-token')), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(diagnostic.main([]), 0)
        path = Path(output.getvalue().splitlines()[0].removeprefix('Diagnostic file: '))
        try:
            self.assertEqual(path.stat().st_mode & 0o777, 0o644)
            self.assertNotIn('secret-token', path.read_text())
        finally:
            path.unlink()
        for failure in (HarnessError('secret-token'), LookupError('secret-token')):
            with patch.object(diagnostic.game_launch,'test_identity',side_effect=failure), patch.object(diagnostic.gateway,'_transport') as transport, contextlib.redirect_stderr(io.StringIO()) as error:
                self.assertEqual(diagnostic.main([]), 2)
            transport.assert_not_called()
            self.assertNotIn('secret-token', error.getvalue())


if __name__ == '__main__':
    unittest.main()
