import http.client
import json
import socket
import threading
import time
import unittest
from unittest import mock
from urllib.parse import urlencode, urlsplit

from harness.gateway import Gateway, MAX_REQUEST, MAX_RESPONSE, _transport


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.calls = []

        def fake(method, url, headers, body):
            self.calls.append((method, url, headers, body))
            return 200, {"Content-Type": "application/json", "ETag": '"ok"',
                         "Set-Cookie": "secret=1", "Location": "https://elsewhere.example/"}, b"{}"

        self.gateway = Gateway(transport=fake).__enter__()

    def tearDown(self):
        self.gateway.close()

    def request(self, url, method="GET", headers=None, body=None, key=None, path="/fetch", raw=None):
        endpoint = urlsplit(self.gateway.url)
        conn = http.client.HTTPConnection(endpoint.hostname, endpoint.port, timeout=2)
        payload = json.dumps({"url": url, "method": method, "headers": headers or {}, "body": body}).encode() if raw is None else raw
        conn.request("POST", path, body=payload, headers={"X-Harness-Key": self.gateway.key if key is None else key,
                                                           "Content-Type": "application/json"})
        response = conn.getresponse()
        result = (response.status, dict(response.getheaders()), response.read())
        conn.close()
        return result

    def request_with_outer_headers(self, outer_headers):
        endpoint = urlsplit(self.gateway.url)
        conn = http.client.HTTPConnection(endpoint.hostname, endpoint.port, timeout=2)
        payload = b'{"url":"https://api.sts2.untapped.gg/api/v1/account","method":"GET","headers":{},"body":null}'
        conn.putrequest("POST", "/fetch")
        conn.putheader("X-Harness-Key", self.gateway.key)
        conn.putheader("Content-Length", str(len(payload)))
        for name, value in outer_headers:
            conn.putheader(name, value)
        conn.endheaders(payload)
        response = conn.getresponse()
        result = response.status
        response.read()
        conn.close()
        return result

    def test_public_get_strips_credentials_and_response_headers(self):
        status, headers, body = self.request("https://sts2json.untapped.gg/data/public/latest/eng/cards.json",
            headers={"Accept": "application/json", "Authorization": "Bearer secret", "Cookie": "session=secret"})
        self.assertEqual((status, body), (200, b"{}"))
        self.assertEqual(headers.get("Content-Type"), "application/json")
        self.assertEqual(headers.get("ETag"), '"ok"')
        self.assertNotIn("Set-Cookie", headers)
        self.assertNotIn("Location", headers)
        self.assertEqual(self.calls[0][2], {"accept": "application/json"})
        self.assertEqual(self.gateway.counts, {("public_json", 200): 1})

    def test_private_oauth_shapes_and_bearer(self):
        form = urlencode({"client_id": "client", "code": "code", "code_verifier": "verifier",
                          "grant_type": "authorization_code", "redirect_uri": "http://127.0.0.1:17791/",
                          "scope": "companion:full-access"})
        self.assertEqual(self.request("https://api.accounts.untapped.gg/o/token", "POST",
            {"Content-Type": "application/x-www-form-urlencoded"}, form)[0], 200)
        self.assertEqual(self.calls[-1][3], form.encode())
        self.assertEqual(self.request("https://api.sts2.untapped.gg/api/v1/features",
            headers={"Authorization": "Bearer token"})[0], 200)
        self.assertEqual(self.calls[-1][2]["authorization"], "Bearer token")
        self.assertEqual(self.request("https://api.sts2.untapped.gg/api/v1/account",
            headers={"Content-Type": "application/json", "Authorization": "Bearer token"})[0], 200)
        self.assertEqual(self.request("https://api.sts2.untapped.gg/api/v1/oauth/tokens/exchange", "POST",
            {"Content-Type": "application/json"}, '{"access_token":"a","client_id":"b"}')[0], 200)
        refresh = "client_id=client&grant_type=refresh_token&refresh_token=token"
        self.assertEqual(self.request("https://api.accounts.untapped.gg/o/token", "POST",
            {"Content-Type": "application/x-www-form-urlencoded"}, refresh)[0], 200)

    def test_tier_route_accepts_only_canonical_version_query(self):
        base = "https://api.sts2.untapped.gg/api/v1/tier-lists/123e4567-e89b-12d3-a456-426614174000/resolve/"
        self.assertEqual(self.request(base + "?game_version=1.2.3")[0], 200)
        for suffix in ("?game_version=1.2.3&other=x", "?game_version=x%2Fy", "?game_version=",
                       "?game_version=a&game_version=b", "?game_version=x%0Ay"):
            with self.subTest(suffix=suffix):
                self.assertEqual(self.request(base + suffix)[0], 403)

    def test_default_deny_and_payload_validation(self):
        good = "https://api.sts2.untapped.gg/api/v1/account"
        bad = [
            (good, "PUT", {}, None),
            ("http://api.sts2.untapped.gg/api/v1/account", "GET", {}, None),
            ("https://api.sts2.untapped.gg:444/api/v1/account", "GET", {}, None),
            ("https://api.sts2.untapped.gg/api/v1/account#x", "GET", {}, None),
            ("https://api.sts2.untapped.gg/api/v1/../account", "GET", {}, None),
            ("https://api.sts2.untapped.gg/api/v1/%2e%2e/account", "GET", {}, None),
            ("https://api.sts2.untapped.gg/api/v1/upload-tokens", "GET", {}, None),
            ("https://sts2json.untapped.gg/data/public/latest/eng/other.json", "GET", {}, None),
            ("https://api.sts2.untapped.gg/api/v1/tier-lists/123/resolve/?game_version=1", "GET", {}, None),
            (good, "GET", {"X-Secret": "x"}, None),
            (good, "GET", {"User-Agent": "caller-controlled"}, None),
            (good, "GET", {}, "unexpected"),
            (good, "GET", {}, ""),
        ]
        for case in bad:
            with self.subTest(case=case):
                self.assertEqual(self.request(*case)[0], 403)
        self.assertEqual(self.request(good, key="wrong")[0], 403)
        self.assertEqual(self.request(good, path="/else")[0], 403)
        self.assertEqual(self.request(good, raw=b'{"url":"x","url":"y"}')[0], 403)
        self.assertEqual(self.calls, [])

    def test_outer_origin_and_duplicate_capability_or_length_denied(self):
        for headers in ([('Origin', 'https://example.com')],
                        [('X-Harness-Key', self.gateway.key)],
                        [('Content-Length', '0')]):
            with self.subTest(headers=headers):
                self.assertEqual(self.request_with_outer_headers(headers), 403)
        self.assertEqual(self.calls, [])

    def test_304_cache_response_is_allowed_without_cookie(self):
        self.gateway._transport = lambda *_: (304, {"ETag": '"fresh"', "Set-Cookie": "secret=1"}, b"")
        status, headers, body = self.request("https://sts2json.untapped.gg/data/public/latest/eng/relics.json",
            headers={"If-None-Match": '"old"', "Cookie": "secret=1", "Content-Type": "application/json"})
        self.assertEqual((status, body), (304, b""))
        self.assertEqual(headers.get("ETag"), '"fresh"')
        self.assertNotIn("Set-Cookie", headers)

    def test_eight_connection_limit_and_close_releases_clients(self):
        endpoint = urlsplit(self.gateway.url)
        clients = []
        server = self.gateway._server
        try:
            for _ in range(8):
                client = socket.create_connection((endpoint.hostname, endpoint.port), timeout=2)
                client.sendall(b"POST /fetch HTTP/1.0\r\n")
                clients.append(client)
            deadline = time.monotonic() + 2
            while len(self.gateway._server._active) < 8 and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertEqual(len(self.gateway._server._active), 8)
            extra = socket.create_connection((endpoint.hostname, endpoint.port), timeout=2)
            clients.append(extra)
            extra.sendall(b"POST /fetch HTTP/1.0\r\n")
            try:
                self.assertEqual(extra.recv(1), b"")
            except ConnectionResetError:
                pass
            self.assertEqual(len(server._active), 8)
            self.gateway.close()
            deadline = time.monotonic() + 2
            while self.gateway._thread.is_alive() and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertFalse(self.gateway._thread.is_alive())
            deadline = time.monotonic() + 2
            while server._active and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertEqual(len(server._active), 0)
        finally:
            for client in clients:
                client.close()

    def test_upstream_total_deadline_stops_trickle(self):
        class FakeSocket:
            def __init__(self):
                self.timeouts = []

            def settimeout(self, value):
                self.timeouts.append(value)

        class FakeResponse:
            status = 200
            headers = {}

            def __init__(self):
                self.fp = type("Buffered", (), {"raw": type("Raw", (), {"_sock": FakeSocket()})()})()

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                pass

            def read1(self, _size):
                return b"x"

        response = FakeResponse()
        opener = mock.Mock()
        opener.open.return_value = response
        with mock.patch("harness.gateway.build_opener", return_value=opener), \
             mock.patch("harness.gateway.time.monotonic", side_effect=[0, 1, 5, 11]):
            with self.assertRaises(TimeoutError):
                _transport("GET", "https://api.sts2.untapped.gg/api/v1/account", {}, None)
        self.assertEqual(response.fp.raw._sock.timeouts, [9, 5])

    def test_close_waits_for_inflight_upstream_handler(self):
        entered = threading.Event()
        release = threading.Event()

        def slow_transport(*_args):
            entered.set()
            release.wait(3)
            return 200, {}, b"ok"

        self.gateway._transport = slow_transport
        server = self.gateway._server
        client_done = threading.Event()

        def client():
            try:
                self.request("https://api.sts2.untapped.gg/api/v1/account")
            except (OSError, http.client.HTTPException):
                pass  # close() deliberately terminates the active client socket.
            finally:
                client_done.set()

        request_thread = threading.Thread(target=client)
        request_thread.start()
        self.assertTrue(entered.wait(2))
        close_done = threading.Event()
        close_result = []

        def close_gateway():
            close_result.append(self.gateway.close())
            close_done.set()

        closer = threading.Thread(target=close_gateway)
        closer.start()
        try:
            self.assertFalse(close_done.wait(0.1))
            release.set()
            self.assertTrue(close_done.wait(3))
            self.assertEqual(close_result, [True])
            self.assertFalse(server._handler_threads)
            counts = self.gateway.counts
            time.sleep(0.05)
            self.assertEqual(self.gateway.counts, counts)
        finally:
            release.set()
            closer.join(3)
            request_thread.join(3)
        self.assertTrue(client_done.is_set())

    def test_token_and_exchange_reject_duplicates_and_bad_scope(self):
        url = "https://api.accounts.untapped.gg/o/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        self.assertEqual(self.request(url, "POST", headers,
            "client_id=a&client_id=b&grant_type=refresh_token&refresh_token=c")[0], 403)
        self.assertEqual(self.request(url, "POST", headers,
            "client_id=a&code=b&code_verifier=c&grant_type=authorization_code&redirect_uri=http%3A%2F%2Flocalhost%3A17791%2F&scope=wrong")[0], 403)
        self.assertEqual(self.request("https://api.sts2.untapped.gg/api/v1/oauth/tokens/exchange", "POST",
            {"Content-Type": "application/json"}, '{"access_token":"a","access_token":"b","client_id":"c"}')[0], 403)
        self.assertEqual(self.calls, [])

    def test_bounds_redirect_and_fixed_error(self):
        url = "https://api.sts2.untapped.gg/api/v1/account"
        self.assertEqual(self.request(url, raw=b"x" * (MAX_REQUEST + 1))[0], 403)
        self.gateway._transport = lambda *_: (302, {"Location": "https://secret.example/"}, b"")
        status, headers, body = self.request(url)
        self.assertEqual((status, body), (403, b"denied"))
        self.assertNotIn("Location", headers)
        self.gateway._transport = lambda *_: (200, {}, b"x" * (MAX_RESPONSE + 1))
        self.assertEqual(self.request(url)[0], 403)


if __name__ == "__main__":
    unittest.main()
