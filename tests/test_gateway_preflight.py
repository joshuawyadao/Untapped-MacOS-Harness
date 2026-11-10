import http.client
import errno
import json
import threading
import time
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlsplit

from harness.gateway import Gateway, exception_fields


class GatewayPreflightTests(unittest.TestCase):
    def test_two_fixed_requests_pass_through_listening_gateway(self):
        calls = []

        def fake(method, url, headers, body):
            calls.append((method, url, headers, body))
            return 401, {"Content-Type": "application/json", "Set-Cookie": "secret=1"}, b'{"error":"inert"}'

        with Gateway(transport=fake) as gateway:
            result = gateway.preflight()
            self.assertTrue(result["passed"])
            self.assertEqual(result["requests_attempted"], 2)
            self.assertEqual(result["maximum_requests"], 2)
            self.assertFalse(result["real_credentials_sent"])
            self.assertEqual([row["route"] for row in result["results"]], ["accounts_account", "oauth_token"])
            self.assertEqual([row["status"] for row in result["results"]], [401, 401])
            self.assertTrue(all(row["response_kind"] == "JSON" for row in result["results"]))
            self.assertTrue(all(row["json_object"] is True for row in result["results"]))
            self.assertEqual(gateway.counts, {("accounts_account", 401): 1, ("oauth_token", 401): 1})
        self.assertEqual([call[1] for call in calls], [
            "https://api.accounts.untapped.gg/api/v1/account", "https://api.accounts.untapped.gg/o/token"])
        self.assertEqual(calls[0][2], {})
        self.assertIsNone(calls[0][3])
        self.assertNotIn("authorization", calls[1][2])
        self.assertNotIn("cookie", calls[1][2])
        form = parse_qs(calls[1][3].decode())
        self.assertEqual(form["code"], ["harness-inert-code"])
        self.assertEqual(form["client_id"], ["harness-inert-client"])
        self.assertEqual(form["code_verifier"], ["harness-inert-verifier"])

    def test_unexpected_first_response_short_circuits(self):
        calls = []

        def fake(method, url, headers, body):
            calls.append(url)
            return 200, {"Content-Type": "application/json"}, b"{}"

        with Gateway(transport=fake) as gateway:
            result = gateway.preflight()
        self.assertFalse(result["passed"])
        self.assertEqual(result["requests_attempted"], 1)
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["results"], [{"route": "accounts_account", "status": 200,
                                               "response_kind": "JSON", "body_bytes": 2,
                                               "json_object": True}])

    def test_wrong_second_kind_fails_after_exactly_two(self):
        calls = []

        def fake(method, url, headers, body):
            calls.append(url)
            media = "application/json" if len(calls) == 1 else "text/html"
            return 401, {"Content-Type": media}, b"{}" if len(calls) == 1 else b"x"

        with Gateway(transport=fake) as gateway:
            result = gateway.preflight()
        self.assertFalse(result["passed"])
        self.assertEqual(result["requests_attempted"], 2)
        self.assertEqual(result["results"][-1]["response_kind"], "HTML")
        self.assertFalse(result["results"][-1]["json_object"])

    def test_malformed_empty_and_scalar_json_401_cannot_pass(self):
        for body in (b"not-json", b"", b"null", b"[]", b"1", b'"text"', b"\xff",
                     b'{"value":NaN}', b'{"value":Infinity}', b'{"value":-Infinity}',
                     b'{"a":1,"a":2}'):
            calls = []

            def fake(method, url, headers, request_body):
                calls.append(url)
                return 401, {"Content-Type": "application/json"}, body

            with self.subTest(body=body), Gateway(transport=fake) as gateway:
                result = gateway.preflight()
            self.assertFalse(result["passed"])
            self.assertEqual(result["requests_attempted"], 1)
            self.assertEqual(len(calls), 1)
            self.assertEqual(result["results"][0]["json_object"], False)
            self.assertEqual(set(result["results"][0]),
                             {"route", "status", "response_kind", "body_bytes", "json_object"})

    def test_preflight_accepts_stream_that_closes_at_declared_length(self):
        class FakeSocket:
            def settimeout(self, _remaining):
                pass

        class FakeResponse:
            status = 401

            def __init__(self):
                self.length = 2
                self.fp = type("Buffered", (), {"raw": type("Raw", (), {"_sock": FakeSocket()})()})()
                self.reads = 0

            def isclosed(self):
                return self.fp is None

            def read1(self, _size):
                self.reads += 1
                self.length = 0
                self.fp = None
                return b"{}"

            def getheader(self, name):
                return "application/json" if name == "Content-Type" else None

        responses = [FakeResponse(), FakeResponse()]
        with Gateway(transport=lambda *_: (401, {"Content-Type": "application/json"}, b"{}")) as gateway:
            with mock.patch("harness.gateway.http.client.HTTPConnection.getresponse", side_effect=responses):
                result = gateway.preflight()
        self.assertTrue(result["passed"])
        self.assertEqual([response.reads for response in responses], [1, 1])

    def test_transport_failure_metadata_contains_no_message(self):
        def fake(*_args):
            raise ConnectionRefusedError(61, "private.example/token=secret")

        with Gateway(transport=fake) as gateway:
            result = gateway.preflight()
            details = gateway.failure_details
            details[0]["route"] = "mutated"
            self.assertEqual(gateway.failure_details[0]["route"], "accounts_account")
            self.assertEqual(gateway.failure_overflow, 0)
        self.assertFalse(result["passed"])
        self.assertEqual(result["requests_attempted"], 1)
        self.assertEqual(result["results"], [{"route": "accounts_account", "status": 502,
                                               "response_kind": "OTHER", "body_bytes": len(b"upstream error"),
                                               "json_object": False}])
        row = gateway.failure_details[0]
        self.assertEqual(row["stage"], "UPSTREAM_TRANSPORT")
        self.assertEqual(row["transport_error"], "CONNECTION_REFUSED")
        self.assertGreaterEqual(row["elapsed_ms"], 0)
        self.assertLessEqual(row["elapsed_ms"], 300000)
        self.assertNotIn("secret", json.dumps(row))

    def test_failure_cap_and_safe_exception_fields(self):
        gateway = Gateway(transport=lambda *_: None)
        for _ in range(34):
            gateway._record_failure("private.example/secret", "bad-stage", time.monotonic() - 9999,
                                    OSError(errno.ECONNREFUSED, "secret"))
        self.assertEqual(len(gateway.failure_details), 32)
        self.assertEqual(gateway.failure_overflow, 2)
        self.assertEqual(gateway.failure_details[0], {"route": "denied", "stage": "LOCAL_REQUEST",
                                                       "elapsed_ms": 300000, "transport_error": "CONNECTION_REFUSED",
                                                       "os_errno": errno.ECONNREFUSED})
        self.assertEqual(exception_fields(AttributeError("secret")), {"transport_error": "RESPONSE_INTERFACE_ERROR"})

    def test_close_drains_failure_before_snapshot(self):
        entered = threading.Event()
        release = threading.Event()

        def fake(*_args):
            entered.set()
            release.wait(3)
            raise TimeoutError("private URL secret")

        gateway = Gateway(transport=fake).__enter__()
        endpoint = urlsplit(gateway.url)

        def client():
            connection = http.client.HTTPConnection(endpoint.hostname, endpoint.port, timeout=2)
            payload = {"url": "https://api.accounts.untapped.gg/api/v1/account", "method": "GET",
                       "headers": {}, "body": None}
            try:
                connection.request("POST", "/fetch", body=json.dumps(payload).encode(),
                                   headers={"X-Harness-Key": gateway.key})
                connection.getresponse().read()
            except (OSError, http.client.HTTPException):
                pass
            finally:
                connection.close()

        client_thread = threading.Thread(target=client)
        client_thread.start()
        self.assertTrue(entered.wait(2))
        closer = threading.Thread(target=gateway.close)
        closer.start()
        release.set()
        closer.join(3)
        client_thread.join(3)
        self.assertTrue(gateway.cleanup_complete)
        self.assertFalse(closer.is_alive())
        before = gateway.failure_details
        self.assertEqual(len(before), 1)
        self.assertEqual(before[0]["transport_error"], "TIMEOUT")
        time.sleep(0.05)
        self.assertEqual(gateway.failure_details, before)


if __name__ == "__main__":
    unittest.main()
