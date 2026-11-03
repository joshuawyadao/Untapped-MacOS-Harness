"""Default-deny loopback gateway for the isolated Untapped companion."""

from __future__ import annotations

import hmac
import json
import re
import secrets
import socket
import ssl
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.parse import parse_qsl, urlsplit
from urllib.request import HTTPSHandler, HTTPRedirectHandler, ProxyHandler, Request, build_opener

MAX_REQUEST = 32768
MAX_RESPONSE = 8 * 1024 * 1024
_UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\Z")
_VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,79}\Z")
_PUBLIC_JSON = frozenset({
    "cards.json", "relics.json", "potions.json", "keywords.json",
    "localization/encounters.json", "localization/enchantments.json",
})
_SAFE_HEADERS = frozenset({"accept", "content-type", "if-none-match", "authorization"})


class Denied(Exception):
    """A request did not meet the gateway contract."""


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Denied()
        result[key] = value
    return result


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

    @property
    def counts(self):
        with self._lock:
            return dict(self._counts)

    def _count(self, route, status):
        with self._lock:
            key = (route, status)
            self._counts[key] = self._counts.get(key, 0) + 1

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
                try:
                    super().process_request_thread(request, client_address)
                finally:
                    with self._active_lock:
                        self._active.discard(request)
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
                    status, upstream_headers, data = gateway._transport(payload["method"], url, headers, body)
                    if not isinstance(status, int) or not 100 <= status <= 599 or (300 <= status < 400 and status != 304) or not isinstance(data, bytes) or len(data) > MAX_RESPONSE:
                        raise Denied()
                    allowed = {k: v for k, v in upstream_headers.items() if k.lower() in ("content-type", "etag")}
                    gateway._count(route, status)
                    self._send(status, data, allowed)
                except (Denied, ValueError, UnicodeDecodeError, TypeError):
                    gateway._count("denied", 403)
                    self._send(403, b"denied")
                except Exception:
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
            self._server = None

    def __exit__(self, *_args):
        self.close()
