"""Bounded, pinned interface to the harness-only macOS Keychain helper."""

import hashlib
import json
import os
import selectors
import stat
import subprocess
import time
from pathlib import Path

from .asar import HarnessError

_LIMIT = 64 * 1024
_TIMEOUT = 20


class KeychainStore:
    def __init__(self, helper: Path, expected_sha256: str, on_warning=None):
        self.helper = Path(helper)
        self.expected_sha256 = expected_sha256
        self.on_warning = on_warning

    def _warn(self):
        if self.on_warning is not None:
            try:
                self.on_warning("Remembered login is unavailable")
            except Exception:
                pass

    def _fail(self):
        self._warn()
        raise HarnessError("Remembered login is unavailable") from None

    def _verify(self, deadline):
        path = self.helper
        try:
            if not path.is_absolute() or path.resolve(strict=True) != path:
                self._fail()
            entry = path.lstat()
            if (not stat.S_ISREG(entry.st_mode) or entry.st_uid != os.getuid()
                    or entry.st_nlink != 1 or stat.S_IMODE(entry.st_mode) != 0o700):
                self._fail()
            if (len(self.expected_sha256) != 64
                    or any(c not in "0123456789abcdef" for c in self.expected_sha256)):
                self._fail()
            descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                opened = os.fstat(descriptor)
                if (opened.st_dev, opened.st_ino) != (entry.st_dev, entry.st_ino):
                    self._fail()
                digest = hashlib.sha256()
                while chunk := os.read(descriptor, 65536):
                    digest.update(chunk)
                if digest.hexdigest() != self.expected_sha256:
                    self._fail()
            finally:
                os.close(descriptor)
            signature = subprocess.run(
                ["/usr/bin/codesign", "--verify", "--strict", str(path)],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, timeout=max(0.001, deadline - time.monotonic()), check=False,
                env={"PATH": "/usr/bin:/bin", "LANG": "C"},
            )
            if signature.returncode != 0:
                self._fail()
        except HarnessError:
            raise
        except (OSError, RuntimeError, TypeError, subprocess.SubprocessError):
            self._fail()

    def _invoke(self, operation, request):
        try:
            payload = json.dumps(request, separators=(",", ":"), ensure_ascii=False,
                                 allow_nan=False).encode("utf-8")
            if len(payload) > _LIMIT:
                self._fail()
            deadline = time.monotonic() + _TIMEOUT
            self._verify(deadline)
            if time.monotonic() >= deadline:
                self._fail()
            process = subprocess.Popen(
                [str(self.helper), operation], stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                close_fds=True, env={"PATH": "/usr/bin:/bin", "LANG": "C"},
            )
            output = bytearray()
            sent = 0
            try:
                with selectors.DefaultSelector() as selector:
                    os.set_blocking(process.stdin.fileno(), False)
                    os.set_blocking(process.stdout.fileno(), False)
                    selector.register(process.stdin, selectors.EVENT_WRITE)
                    selector.register(process.stdout, selectors.EVENT_READ)
                    while selector.get_map():
                        if time.monotonic() >= deadline:
                            self._fail()
                        for key, _ in selector.select(max(0, deadline - time.monotonic())):
                            if key.fileobj is process.stdin:
                                if sent == len(payload):
                                    selector.unregister(process.stdin)
                                    process.stdin.close()
                                else:
                                    sent += os.write(process.stdin.fileno(), payload[sent:])
                            else:
                                chunk = os.read(process.stdout.fileno(), min(4096, _LIMIT + 1 - len(output)))
                                if not chunk:
                                    selector.unregister(process.stdout)
                                    process.stdout.close()
                                else:
                                    output.extend(chunk)
                                    if len(output) > _LIMIT:
                                        self._fail()
                if process.wait(timeout=max(0, deadline - time.monotonic())) != 0:
                    self._fail()
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
                if process.stdin and not process.stdin.closed:
                    process.stdin.close()
                if process.stdout and not process.stdout.closed:
                    process.stdout.close()
            response = json.loads(output)
            if not isinstance(response, dict):
                self._fail()
            return response
        except HarnessError:
            raise
        except (OSError, ValueError, TypeError, OverflowError, subprocess.SubprocessError):
            self._fail()

    def load(self) -> dict:
        response = self._invoke("load", {})
        if set(response) != {"value"} or not isinstance(response["value"], dict):
            self._fail()
        return response["value"]

    def save(self, value: dict) -> None:
        if not isinstance(value, dict):
            self._fail()
        if self._invoke("save", {"value": value}) != {"success": True}:
            self._fail()

    def clear(self) -> None:
        if self._invoke("clear", {}) != {"success": True}:
            self._fail()
