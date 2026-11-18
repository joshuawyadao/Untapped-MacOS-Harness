"""Run a bounded native process scan in one reusable, unprivileged worker."""

from contextlib import contextmanager
import locale
import socket
import subprocess
import tempfile
import time
from pathlib import Path

from . import reward_probe
from .asar import HarnessError

TIMEOUT = 2
MAX_RESPONSE = 1024 * 1024
COMMAND = "native process inventory"


class LiveInventory:
    def __init__(self, executable):
        self.executable = executable
        self.process = None
        self.channel = None

    def _start(self):
        channel, child = socket.socketpair()
        try:
            with child:
                self.process = subprocess.Popen([str(self.executable)], stdin=child, stdout=child,
                                                stderr=subprocess.DEVNULL)
        except BaseException:
            channel.close()
            raise
        self.channel = channel

    def close(self):
        if self.channel is not None:
            self.channel.close()
            self.channel = None
        if self.process is not None:
            self.process.kill()
            self.process.wait()
            self.process = None

    def _exchange(self, deadline):
        if self.channel is None:
            self._start()
        self.channel.settimeout(self._remaining(deadline))
        self.channel.sendall(b"\n")
        response = bytearray()
        while len(response) < MAX_RESPONSE:
            self.channel.settimeout(self._remaining(deadline))
            chunk = self.channel.recv(min(65536, MAX_RESPONSE - len(response)))
            if not chunk:
                raise subprocess.CalledProcessError(1, COMMAND)
            response.extend(chunk)
            if response[-1] in (0, 1):
                return response[:-1], response[-1]
        raise HarnessError("Native inventory response is too large")

    @staticmethod
    def _remaining(deadline):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(COMMAND, TIMEOUT)
        return remaining

    def candidates(self):
        deadline = time.monotonic() + TIMEOUT
        try:
            payload, fallback = self._exchange(deadline)
            if fallback:
                listing = reward_probe._process_inventory(timeout=self._remaining(deadline))
            else:
                listing = payload.decode(locale.getpreferredencoding(False))
            return list(reward_probe._candidates(listing))
        except (socket.timeout, subprocess.TimeoutExpired) as error:
            self.close()
            raise subprocess.TimeoutExpired(COMMAND, TIMEOUT) from error
        except (BrokenPipeError, ConnectionResetError) as error:
            self.close()
            raise subprocess.CalledProcessError(1, COMMAND) from error
        except BaseException:
            self.close()
            raise


@contextmanager
def prepare(attempt):
    source = Path(__file__).with_name("live_inventory.c")
    with tempfile.TemporaryDirectory(prefix="inventory-", dir=attempt) as directory:
        helper = Path(directory) / "live-inventory"
        subprocess.run(["/usr/bin/clang", "-Wall", "-Wextra", "-Werror", "-Os",
                        str(source), "-o", str(helper)], cwd=directory, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
        inventory = LiveInventory(helper)
        try:
            yield inventory.candidates
        finally:
            inventory.close()
