"""Private, session-scoped bridge between the companion and its Keychain item."""

from __future__ import annotations

import hmac
import json
import os
from pathlib import Path
import re
import secrets
import socket
import stat
import threading
import time
from typing import Callable

from .asar import HarnessError


_MAX_MESSAGE = 64 * 1024
# Pinned Services chunk: `Untapped Companion ${UC_TEST_SANDBOX_ID}`.
_SERVICE = 'Untapped Companion native-sts2-harness'
_ACCOUNT = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._%+\-]*@[A-Za-z0-9][A-Za-z0-9.\-]*\.[A-Za-z]{2,}$')


def _valid_account(value: object) -> bool:
    return isinstance(value, str) and 3 <= len(value) <= 254 and bool(_ACCOUNT.fullmatch(value))


def _token_password(value: object) -> str | None:
    """Return a minimal serialized global OAuth token, or no persistable value."""
    if not isinstance(value, str):
        return None
    try:
        if len(value.encode('utf-8')) > _MAX_MESSAGE:
            return None
    except UnicodeEncodeError:
        return None
    try:
        parsed = json.loads(value)
    except (ValueError, TypeError):
        return None
    if not isinstance(parsed, dict):
        return None
    global_token = parsed.get('globalOAuthAccessToken')
    if not isinstance(global_token, dict):
        return None
    if global_token.get('isInvalid') is True:
        return ''
    access = global_token.get('accessToken')
    refresh = global_token.get('refreshToken')
    for token in (access, refresh):
        if not isinstance(token, str):
            return None
        try:
            if not 0 < len(token.encode('utf-8')) <= 16 * 1024:
                return None
        except UnicodeEncodeError:
            return None
    return json.dumps({'globalOAuthAccessToken': {
        'accessToken': access, 'refreshToken': refresh,
    }}, separators=(',', ':'))


class RememberBroker:
    """Serve one launch's credential capability from a private Unix socket."""

    def __init__(self, attempt: Path, store: object,
                 on_warning: Callable[[str], None] | None = None):
        self._attempt_input = Path(attempt)
        self.attempt = self._attempt_input.resolve()
        self.store = store
        self.on_warning = on_warning
        self.socket_path = self.attempt / 'remember.sock'
        self.capability = secrets.token_hex(32)
        self.environment = {
            'UNTAPPED_HARNESS_LOGIN_SOCKET': str(self.socket_path),
            'UNTAPPED_HARNESS_LOGIN_CAPABILITY': self.capability,
        }
        self._credentials: dict[str, str] = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._slots = threading.BoundedSemaphore(4)
        self._threads: set[threading.Thread] = set()
        self._threads_lock = threading.Lock()
        self._server: socket.socket | None = None
        self._accept_thread: threading.Thread | None = None
        self._close_lock = threading.Lock()
        self._closed = False

    def _warn(self) -> None:
        if self.on_warning:
            try:
                self.on_warning('Remembered login is unavailable; sign in manually.')
            except Exception:
                pass

    def __enter__(self) -> RememberBroker:
        if not self._attempt_input.is_absolute() or self.attempt.resolve(strict=True) != self.attempt:
            raise HarnessError('Remember-login attempt directory must be canonical')
        source_info = self._attempt_input.lstat()
        if not stat.S_ISDIR(source_info.st_mode):
            raise HarnessError('Remember-login attempt directory must be a real directory')
        info = self.attempt.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise HarnessError('Remember-login attempt directory must be private and owned')
        if self.socket_path.exists() or self.socket_path.is_symlink():
            raise HarnessError('Remember-login socket already exists')
        try:
            loaded = self.store.load()
            if not isinstance(loaded, dict):
                raise HarnessError('Invalid remembered login data')
            for account, password in loaded.items():
                if _valid_account(account):
                    minimal = _token_password(password)
                    if minimal:
                        self._credentials = {account: minimal}
                        break
        except Exception:
            self._warn()
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            server.bind(str(self.socket_path))
            os.chmod(self.socket_path, 0o600)
            server.listen(4)
            server.settimeout(0.2)
        except Exception:
            server.close()
            self.socket_path.unlink(missing_ok=True)
            raise
        self._server = server
        self._accept_thread = threading.Thread(target=self._accept, daemon=True)
        self._accept_thread.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        """Stop accepting writes and drain every in-flight helper operation."""
        with self._close_lock:
            if self._closed:
                return
            self._stop.set()
            deadline = time.monotonic() + 22
            if self._server:
                self._server.close()
            if self._accept_thread:
                self._accept_thread.join(timeout=min(2, max(0, deadline - time.monotonic())))
            with self._threads_lock:
                threads = tuple(self._threads)
            for thread in threads:
                thread.join(timeout=max(0, deadline - time.monotonic()))
            if (self._accept_thread and self._accept_thread.is_alive()) or any(thread.is_alive() for thread in threads):
                raise HarnessError('Remember-login broker did not finish pending writes')
            self.socket_path.unlink(missing_ok=True)
            self._closed = True

    def _accept(self) -> None:
        assert self._server is not None
        while not self._stop.is_set():
            try:
                client, _ = self._server.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            if self._stop.is_set():
                client.close()
                break
            if not self._slots.acquire(blocking=False):
                client.close()
                continue
            thread = threading.Thread(target=self._handle, args=(client,), daemon=True)
            with self._threads_lock:
                self._threads.add(thread)
            thread.start()

    def _handle(self, client: socket.socket) -> None:
        try:
            with client:
                client.settimeout(2)
                data = bytearray()
                while len(data) <= _MAX_MESSAGE and b'\n' not in data:
                    chunk = client.recv(min(4096, _MAX_MESSAGE + 1 - len(data)))
                    if not chunk:
                        return
                    data.extend(chunk)
                if len(data) > _MAX_MESSAGE or not data.endswith(b'\n'):
                    return
                try:
                    request = json.loads(data[:-1])
                    response = self._dispatch(request)
                except (ValueError, TypeError, UnicodeDecodeError):
                    response = {'ok': False}
                client.sendall(json.dumps(response, separators=(',', ':')).encode() + b'\n')
        except (OSError, TimeoutError):
            pass
        finally:
            self._slots.release()
            with self._threads_lock:
                self._threads.discard(threading.current_thread())

    def _dispatch(self, request: object) -> dict:
        if not isinstance(request, dict) or not isinstance(request.get('capability'), str) or not hmac.compare_digest(request['capability'], self.capability):
            return {'ok': False}
        op = request.get('op')
        if op == 'load':
            with self._lock:
                if self._stop.is_set():
                    return {'ok': False}
                return {'ok': True, 'credentials': [
                    {'account': account, 'password': password}
                    for account, password in self._credentials.items()
                ]}
        if op not in ('set', 'delete') or request.get('service') != _SERVICE or not _valid_account(request.get('account')):
            return {'ok': False}
        account = request['account']
        with self._lock:
            if self._stop.is_set():
                return {'ok': False}
            if op == 'set':
                password = _token_password(request.get('password'))
                if password is None:
                    return {'ok': False}
                next_credentials = {} if password == '' else {account: password}
            else:
                next_credentials = dict(self._credentials)
                next_credentials.pop(account, None)
            self._credentials = next_credentials
            try:
                if next_credentials:
                    self.store.save(dict(next_credentials))
                else:
                    self.store.clear()
            except Exception:
                self._warn()
            return {'ok': True}
