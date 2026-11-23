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
CLEANUP_TIMEOUT = 0.1
MAX_RESPONSE = 1024 * 1024
COMMAND = "native process inventory"
TIMEOUT_PHASES = frozenset({"NATIVE_START", "NATIVE_RESPONSE", "NATIVE_REAP",
                            "LEGACY_START", "LEGACY_RESPONSE", "LEGACY_REAP"})


class InventoryTimeout(subprocess.TimeoutExpired):
    def __init__(self, phase):
        super().__init__(COMMAND, TIMEOUT)
        self.phase = phase


class LiveInventory:
    def __init__(self, executable):
        self.executable = executable
        self.process = None
        self.channel = None
        self._retired = {}
        self._use_legacy = False

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

    def _retire(self, backend, process):
        self._retired[backend] = process
        process.kill()

    def _reap_retired(self):
        for backend, process in tuple(self._retired.items()):
            if process.poll() is not None:
                del self._retired[backend]

    def _stop_native(self):
        if self.channel is not None:
            self.channel.close()
            self.channel = None
        if self.process is not None:
            process, self.process = self.process, None
            self._retire("NATIVE", process)

    def close(self):
        self._stop_native()
        self._reap_retired()
        deadline = time.monotonic() + CLEANUP_TIMEOUT
        for backend, process in tuple(self._retired.items()):
            try:
                process.wait(timeout=max(0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                # It has already been signalled. A kernel-stalled child must not hold up session close.
                continue
            del self._retired[backend]

    def _exchange(self, deadline):
        if self.channel is None:
            if "NATIVE" in self._retired:
                raise InventoryTimeout("NATIVE_REAP")
            self._start()
            self._remaining(deadline, "NATIVE_START")
        try:
            self.channel.settimeout(self._remaining(deadline, "NATIVE_RESPONSE"))
            self.channel.sendall(b"\n")
            response = bytearray()
            while len(response) < MAX_RESPONSE:
                self.channel.settimeout(self._remaining(deadline, "NATIVE_RESPONSE"))
                chunk = self.channel.recv(min(65536, MAX_RESPONSE - len(response)))
                if not chunk:
                    raise subprocess.CalledProcessError(1, COMMAND)
                response.extend(chunk)
                if response[-1] in (0, 1):
                    self._remaining(deadline, "NATIVE_RESPONSE")
                    return response[:-1], response[-1]
        except socket.timeout as error:
            raise InventoryTimeout("NATIVE_RESPONSE") from error
        raise HarnessError("Native inventory response is too large")

    @staticmethod
    def _remaining(deadline, phase):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise InventoryTimeout(phase)
        return remaining

    def _legacy_listing(self, deadline):
        if "LEGACY" in self._retired:
            raise InventoryTimeout("LEGACY_REAP")
        self._remaining(deadline, "LEGACY_START")
        process = subprocess.Popen(reward_probe.PROCESS_INVENTORY_COMMAND, stdout=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL, text=True)
        with process.stdout:
            try:
                remaining = self._remaining(deadline, "LEGACY_START")
                try:
                    listing, _ = process.communicate(timeout=remaining)
                except subprocess.TimeoutExpired as error:
                    raise InventoryTimeout("LEGACY_RESPONSE") from error
                if process.returncode:
                    raise subprocess.CalledProcessError(process.returncode, COMMAND)
                self._remaining(deadline, "LEGACY_RESPONSE")
                return listing
            finally:
                if process.returncode is None:
                    self._retire("LEGACY", process)

    def candidates(self):
        deadline = time.monotonic() + TIMEOUT
        self._reap_retired()
        alternate = self._use_legacy
        self._use_legacy = False
        try:
            if alternate:
                listing = self._legacy_listing(deadline)
            else:
                payload, fallback = self._exchange(deadline)
                listing = (self._legacy_listing(deadline) if fallback
                           else payload.decode(locale.getpreferredencoding(False)))
            return list(reward_probe._candidates(listing))
        except InventoryTimeout as error:
            if error.phase.startswith("NATIVE_"):
                self._stop_native()
                self._use_legacy = True
            raise
        except (BrokenPipeError, ConnectionResetError) as error:
            self._stop_native()
            raise subprocess.CalledProcessError(1, COMMAND) from error
        except BaseException:
            self._stop_native()
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
