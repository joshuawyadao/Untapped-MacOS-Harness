"""On-wire regression for the original companion's HTTP client identity."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import unittest

from harness.gateway import _transport


class GatewayClientTests(unittest.TestCase):
    def test_transport_sends_the_pinned_companion_user_agent(self):
        # Reproduce the measured upstream distinction using an original inert
        # local server. No vendor code, remote endpoint or credentials are used.
        original_agent = 'node-fetch/1.0 (+https://github.com/bitinn/node-fetch)'
        seen = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_GET(self):
                seen.append(dict(self.headers))
                matches = self.headers.get('User-Agent') == original_agent
                body = b'{"detail":"Authentication credentials were not provided."}' if matches else b'client rejected'
                self.send_response(401 if matches else 403)
                self.send_header('Content-Type', 'application/json' if matches else 'text/plain')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            status, headers, body = _transport('GET', f'http://127.0.0.1:{server.server_port}/account', {}, None)
            self.assertEqual(status, 401, 'Gateway must retain the original client header at the HTTP boundary')
            self.assertEqual(headers['Content-Type'], 'application/json')
            self.assertIn(b'credentials were not provided', body)
            self.assertEqual(len(seen), 1)
            self.assertEqual(seen[0]['User-Agent'], original_agent)
            self.assertNotIn('Authorization', seen[0])
            self.assertNotIn('Cookie', seen[0])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == '__main__':
    unittest.main()
