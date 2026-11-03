"""Default-deny loopback gateway for the isolated Untapped companion."""

from __future__ import annotations

import hmac
import http.client
import json
import re
import secrets
import socket
import ssl
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.parse import parse_qsl, urlencode, urlsplit
from urllib.request import HTTPSHandler, HTTPRedirectHandler, ProxyHandler, Request, build_opener

MAX_REQUEST = 32768
MAX_RESPONSE = 8 * 1024 * 1024
# Pinned original node-fetch default; never supplied by an app request or env.
COMPANION_USER_AGENT = "node-fetch/1.0 (+https://github.com/bitinn/node-fetch)"
_UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\Z")
_VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,79}\Z")
_PUBLIC_JSON = frozenset({
    "cards.json", "relics.json", "potions.json", "keywords.json",
    "localization/encounters.json", "localization/enchantments.json",
})
_SAFE_HEADERS = frozenset({"accept", "content-type", "if-none-match", "authorization"})
_ROUTE_IDS = frozenset({"oauth_token", "accounts_account", "sts2_exchange", "sts2_account",
                        "sts2_features", "tier_resolve", "public_json", "commentary_events"})


def exception_fields(error):
    """Classify an exception without copying its message, URL or response."""
    cause = error
    for _ in range(3):
        if isinstance(cause, URLError):
            cause = cause.reason
        else:
            break
    if isinstance(cause, ssl.SSLCertVerificationError):
        category = "TLS_CERTIFICATE_ERROR"
    elif isinstance(cause, ssl.SSLError):
        category = "TLS_PROTOCOL_ERROR"
    elif isinstance(cause, socket.gaierror):
        category = "DNS_ERROR"
    elif isinstance(cause, TimeoutError):
        category = "TIMEOUT"
    elif isinstance(cause, http.client.IncompleteRead):
        category = "INCOMPLETE_RESPONSE"
    elif isinstance(cause, ConnectionRefusedError):
        category = "CONNECTION_REFUSED"
    elif isinstance(cause, (ConnectionError, http.client.RemoteDisconnected)):
        category = "CONNECTION_CLOSED"
    elif isinstance(cause, OSError):
        category = "OS_ERROR"
    elif isinstance(cause, AttributeError):
        category = "RESPONSE_INTERFACE_ERROR"
    elif isinstance(cause, (TypeError, ValueError)):
        category = "INTERNAL_SHAPE_ERROR"
    else:
        category = "UNKNOWN_TRANSPORT_ERROR"
    fields = {"transport_error": category}
    for attribute, field in (("errno", "os_errno"), ("verify_code", "certificate_verify_code")):
        value = getattr(cause, attribute, None)
        if type(value) is int and -65536 <= value <= 65536:
            fields[field] = value
    return fields


class Denied(Exception):
    """A request did not meet the gateway contract."""


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Denied()
        result[key] = value
    return result


def _reject_json_constant(_value):
    raise ValueError()


def _text_safe(value):
    return isinstance(value, str) and not any(ord(c) < 32 or ord(c) == 127 for c in value)


def _route(url, method):
    if not _text_safe(url) or "\\" in url:
        raise Denied()
    try:
        p = urlsplit(url)
        port = p.port
    except ValueError as exc:
        raise Denied() from exc
    if (p.scheme != "https" or p.username is not None or p.password is not None
            or p.fragment or port not in (None, 443) or not p.hostname
            or p.netloc.lower() not in (p.hostname.lower(), p.hostname.lower() + ":443")
            or "%" in p.path or "//" in p.path or "/./" in p.path or "/../" in p.path):
        raise Denied()
    host, path = p.hostname.lower(), p.path
    if host == "api.accounts.untapped.gg" and method == "POST" and path == "/o/token" and not p.query:
        return "oauth_token", False
    if host == "api.accounts.untapped.gg" and method == "GET" and path == "/api/v1/account" and not p.query:
        return "accounts_account", False
    if host == "api.sts2.untapped.gg" and not p.query:
        if method == "POST" and path == "/api/v1/oauth/tokens/exchange":
            return "sts2_exchange", False
        if method == "GET" and path == "/api/v1/account":
            return "sts2_account", False
        if method == "GET" and path == "/api/v1/features":
            return "sts2_features", False
    if host == "api.sts2.untapped.gg" and method == "GET":
        match = re.fullmatch(r"/api/v1/tier-lists/([^/]+)/resolve/", path)
        if match and _UUID.fullmatch(match.group(1)):
            if p.query:
                query = parse_qsl(p.query, keep_blank_values=True, strict_parsing=True)
                if len(query) != 1 or query[0][0] != "game_version" or not _VERSION.fullmatch(query[0][1]):
                    raise Denied()
            return "tier_resolve", True
    if host == "sts2json.untapped.gg" and method == "GET" and not p.query:
        if path.startswith("/data/public/latest/eng/") and path.removeprefix("/data/public/latest/eng/") in _PUBLIC_JSON:
            return "public_json", True
    if host == "sts2.untapped.gg" and method == "GET" and path == "/api/v1/commentary/events" and not p.query:
        return "commentary_events", True
    raise Denied()


def _validate(payload):
    if not isinstance(payload, dict) or set(payload) != {"url", "method", "headers", "body"}:
        raise Denied()
    url, method, supplied, body = (payload[k] for k in ("url", "method", "headers", "body"))
    if method not in ("GET", "POST") or not isinstance(supplied, dict) or not isinstance(body, (str, type(None))):
        raise Denied()
    route, public = _route(url, method)
    headers = {}
    for name, value in supplied.items():
        if not _text_safe(name) or not _text_safe(value) or not name or not name.isascii() or name.lower() in headers:
            raise Denied()
        lower = name.lower()
        if lower in _SAFE_HEADERS and (lower != "authorization" or not public):
            headers[lower] = value
        elif lower != "cookie" and lower != "authorization":
            raise Denied()
    if "authorization" in headers:
        auth = headers["authorization"]
        if route == "oauth_token" or not re.fullmatch(r"Bearer [A-Za-z0-9._~+/=-]{1,8192}", auth):
            raise Denied()
    if method == "GET":
        if body is not None:
            raise Denied()
        if "content-type" in headers:
            if public:
                headers.pop("content-type")
            elif route in ("sts2_account", "sts2_features") and headers["content-type"].split(";")[0].strip().lower() == "application/json":
                pass
            else:
                raise Denied()
        return route, url, headers, None
    if body is None:
        raise Denied()
    raw = body.encode("utf-8")
    if len(raw) > MAX_REQUEST:
        raise Denied()
    if route == "oauth_token":
        if headers.get("content-type", "").split(";")[0].strip().lower() != "application/x-www-form-urlencoded":
            raise Denied()
        try:
            pairs = parse_qsl(body, keep_blank_values=True, strict_parsing=True, max_num_fields=6)
        except ValueError as exc:
            raise Denied() from exc
        fields = _unique_object(pairs)
        if fields.get("grant_type") == "authorization_code":
            if set(fields) != {"client_id", "code", "code_verifier", "grant_type", "redirect_uri", "scope"} or fields["scope"] != "companion:full-access":
                raise Denied()
            callback = urlsplit(fields["redirect_uri"])
            if (callback.scheme != "http" or callback.hostname not in ("localhost", "127.0.0.1")
                    or callback.port not in range(17791, 17800) or callback.path != "/"
                    or callback.query or callback.fragment or callback.username or callback.password):
                raise Denied()
        elif fields.get("grant_type") == "refresh_token":
            if set(fields) != {"client_id", "grant_type", "refresh_token"}:
                raise Denied()
        else:
            raise Denied()
        if any(not _text_safe(v) or not v for v in fields.values()):
            raise Denied()
    elif route == "sts2_exchange":
        if headers.get("content-type", "").split(";")[0].strip().lower() != "application/json":
            raise Denied()
        try:
            data = json.loads(body, object_pairs_hook=_unique_object)
        except (ValueError, TypeError) as exc:
            raise Denied() from exc
        if not isinstance(data, dict) or set(data) != {"access_token", "client_id"} or any(not _text_safe(v) or not v for v in data.values()):
            raise Denied()
    else:
        raise Denied()
    return route, url, headers, raw


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def _transport(method, url, headers, body):
    opener = build_opener(ProxyHandler({}), HTTPSHandler(context=ssl.create_default_context()), _NoRedirect())
    request = Request(url, data=body, headers=headers, method=method)
    request.add_header("User-Agent", COMPANION_USER_AGENT)
    deadline = time.monotonic() + 10
    try:
        response = opener.open(request, timeout=10)
    except HTTPError as exc:
        response = exc
    with response:
        status = response.status
        if 300 <= status < 400 and status != 304:
            raise Denied()
        chunks = []
        size = 0
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError()
            # urllib's timeout applies per read. Shorten it to the remaining
            # total budget so a slow stream cannot reset the deadline.
            try:
                stream = response.fp
                if hasattr(stream, "fp"):
                    stream = stream.fp
                stream.raw._sock.settimeout(remaining)
            except AttributeError:
                pass
            chunk = response.read1(min(65536, MAX_RESPONSE + 1 - size))
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_RESPONSE:
                raise Denied()
            chunks.append(chunk)
        return status, dict(response.headers.items()), b"".join(chunks)


class Gateway:
    def __init__(self, transport=None):
        self.key = secrets.token_urlsafe(32)
        self.url = ""
        self._transport = transport or _transport
        self._lock = threading.Lock()
        self._counts = {}
        self._server = None
        self._thread = None
        self.cleanup_complete = True
        self._failure_details = []
        self._failure_overflow = 0

    @property
    def counts(self):
        with self._lock:
            return dict(self._counts)

    @property
    def failure_details(self):
        with self._lock:
            return [dict(row) for row in self._failure_details]

    @property
    def failure_overflow(self):
        with self._lock:
            return self._failure_overflow

    def _count(self, route, status):
        with self._lock:
            key = (route, status)
            self._counts[key] = self._counts.get(key, 0) + 1

    def _record_failure(self, route, stage, started, error):
        row = {"route": route if route in _ROUTE_IDS else "denied",
               "stage": stage if stage in ("LOCAL_REQUEST", "UPSTREAM_TRANSPORT",
                                           "UPSTREAM_RESPONSE", "LOCAL_RESPONSE") else "LOCAL_REQUEST",
               "elapsed_ms": max(0, min(300000, int((time.monotonic() - started) * 1000))),
               **exception_fields(error)}
        with self._lock:
            if len(self._failure_details) < 32:
                self._failure_details.append(row)
            else:
                self._failure_overflow += 1

    def preflight(self):
        """Exercise the live loopback gateway with two fixed inert requests."""
        requests = (
            {"url": "https://api.accounts.untapped.gg/api/v1/account", "method": "GET", "headers": {}, "body": None},
            {"url": "https://api.accounts.untapped.gg/o/token", "method": "POST",
             "headers": {"Content-Type": "application/x-www-form-urlencoded"},
             "body": urlencode({"client_id": "harness-inert-client", "code": "harness-inert-code",
                                "code_verifier": "harness-inert-verifier", "grant_type": "authorization_code",
                                "redirect_uri": "http://localhost:17791/", "scope": "companion:full-access"})},
        )
        result = {"passed": False, "results": [], "requests_attempted": 0,
                  "maximum_requests": 2, "real_credentials_sent": False}
        if not self._server or not self._thread.is_alive():
            return result
        deadline = time.monotonic() + 15
        port = urlsplit(self.url).port
        for request in requests:
            route, _, _, _ = _validate(request)
            row = {"route": route}
            result["requests_attempted"] += 1
            connection = None
            try:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError()
                connection = http.client.HTTPConnection("127.0.0.1", port, timeout=remaining)
                connection.request("POST", "/fetch", body=json.dumps(request).encode("utf-8"),
                                   headers={"X-Harness-Key": self.key, "Content-Type": "application/json"})
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError()
                if connection.sock:
                    connection.sock.settimeout(remaining)
                response = connection.getresponse()
                size = 0
                chunks = []
                while True:
                    if response.isclosed() or response.length == 0:
                        break
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError()
                    response.fp.raw._sock.settimeout(remaining)
                    chunk = response.read1(min(8192, 32769 - size))
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > 32768:
                        raise ValueError()
                    chunks.append(chunk)
                media = (response.getheader("Content-Type") or "").split(";")[0].strip().lower()
                kind = {"application/json": "JSON", "text/plain": "TEXT", "text/html": "HTML"}.get(media, "OTHER")
                json_object = False
                if kind == "JSON":
                    try:
                        json_object = isinstance(json.loads(b"".join(chunks).decode("utf-8"),
                                                            object_pairs_hook=_unique_object,
                                                            parse_constant=_reject_json_constant), dict)
                    except (Denied, ValueError, UnicodeDecodeError, RecursionError):
                        pass
                row.update(status=response.status, response_kind=kind, body_bytes=size,
                           json_object=json_object)
            except Exception as error:
                row.update(exception_fields(error))
                result["results"].append(row)
                break
            finally:
                if connection:
                    connection.close()
            result["results"].append(row)
            if row["status"] != 401 or row["response_kind"] != "JSON" or not row["json_object"]:
                break
        result["passed"] = len(result["results"]) == 2 and all(
            row.get("status") == 401 and row.get("response_kind") == "JSON" and row.get("json_object") is True
            for row in result["results"]
        )
        return result

    def __enter__(self):
        gateway = self

        class BoundedServer(ThreadingHTTPServer):
            daemon_threads = True

            def handle_error(self, _request, _client_address):
                # HTTP library tracebacks may contain request metadata.
                pass

            def __init__(self, *args, **kwargs):
                self._slots = threading.BoundedSemaphore(8)
                self._active = set()
                self._active_lock = threading.Lock()
                self._handler_threads = set()
                super().__init__(*args, **kwargs)

            def process_request(self, request, client_address):
                if not self._slots.acquire(blocking=False):
                    request.close()
                    return
                try:
                    with self._active_lock:
                        self._active.add(request)
                    super().process_request(request, client_address)
                except Exception:
                    with self._active_lock:
                        self._active.discard(request)
                    self._slots.release()
                    raise

            def process_request_thread(self, request, client_address):
                thread = threading.current_thread()
                with self._active_lock:
                    self._handler_threads.add(thread)
                try:
                    super().process_request_thread(request, client_address)
                finally:
                    with self._active_lock:
                        self._active.discard(request)
                        self._handler_threads.discard(thread)
                    self._slots.release()

            def close_clients(self):
                with self._active_lock:
                    requests = tuple(self._active)
                for request in requests:
                    try:
                        request.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
                    request.close()

        class Handler(BaseHTTPRequestHandler):
            def setup(self):
                self.request.settimeout(5)
                super().setup()

            def log_message(self, *_args):
                pass

            def _send(self, status, data=b"", headers=None):
                self.send_response(status)
                for name, value in (headers or {}).items():
                    if name.lower() in ("content-type", "etag") and _text_safe(value):
                        self.send_header(name, value)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_POST(self):
                route = "denied"
                stage = "LOCAL_REQUEST"
                started = time.monotonic()
                try:
                    if self.client_address[0] != "127.0.0.1" or self.path != "/fetch":
                        raise Denied()
                    if (self.headers.get("Origin") is not None or
                            len(self.headers.get_all("X-Harness-Key", [])) != 1 or
                            len(self.headers.get_all("Content-Length", [])) != 1 or
                            len(self.headers.get_all("Content-Type", [])) > 1):
                        raise Denied()
                    provided = self.headers.get("X-Harness-Key", "")
                    if not hmac.compare_digest(provided, gateway.key):
                        raise Denied()
                    length = self.headers.get("Content-Length", "")
                    if not length.isascii() or not length.isdecimal() or int(length) > MAX_REQUEST or self.headers.get("Transfer-Encoding"):
                        raise Denied()
                    payload = json.loads(self.rfile.read(int(length)), object_pairs_hook=_unique_object)
                    route, url, headers, body = _validate(payload)
                    stage = "UPSTREAM_TRANSPORT"
                    status, upstream_headers, data = gateway._transport(payload["method"], url, headers, body)
                    stage = "UPSTREAM_RESPONSE"
                    if not isinstance(status, int) or not 100 <= status <= 599 or (300 <= status < 400 and status != 304) or not isinstance(data, bytes) or len(data) > MAX_RESPONSE:
                        raise Denied()
                    allowed = {k: v for k, v in upstream_headers.items() if k.lower() in ("content-type", "etag")}
                    gateway._count(route, status)
                    stage = "LOCAL_RESPONSE"
                    self._send(status, data, allowed)
                except (Denied, ValueError, UnicodeDecodeError, TypeError):
                    gateway._count("denied", 403)
                    self._send(403, b"denied")
                except Exception as error:
                    gateway._record_failure(route, stage, started, error)
                    gateway._count("error", 502)
                    self._send(502, b"upstream error")

            def do_GET(self):
                gateway._count("denied", 403)
                self._send(403, b"denied")

        self._server = BoundedServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self._server.server_port}/fetch"
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def close(self):
        if self._server:
            self._server.shutdown()
            self._server.close_clients()
            self._server.server_close()
            self._thread.join(timeout=2)
            deadline = time.monotonic() + 11
            with self._server._active_lock:
                handlers = tuple(self._server._handler_threads)
            for handler in handlers:
                if handler is not threading.current_thread():
                    handler.join(timeout=max(0, deadline - time.monotonic()))
            self.cleanup_complete = not self._thread.is_alive() and not any(
                handler.is_alive() for handler in handlers
            )
            self._server = None
        return self.cleanup_complete

    def __exit__(self, *_args):
        self.close()
