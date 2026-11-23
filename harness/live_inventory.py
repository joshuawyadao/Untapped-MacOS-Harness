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
MAX_SCOPED_PIDS = 128
COMMAND = "native process inventory"
TIMEOUT_PHASES = frozenset(f"{backend}_{stage}" for backend in ("NATIVE", "SCOPED", "LEGACY")
                           for stage in ("START", "RESPONSE", "REAP"))


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

    def _legacy_listing(self, deadline, *, pids=()):
        backend = "SCOPED" if pids else "LEGACY"
        start, response = f"{backend}_START", f"{backend}_RESPONSE"
        if "LEGACY" in self._retired:
            raise InventoryTimeout(f"{backend}_REAP")
        command = reward_probe.PROCESS_INVENTORY_COMMAND
        if pids:
            command = (command[0], "-p", ",".join(pids), "-o", command[-1])
        self._remaining(deadline, start)
        process = subprocess.Popen(command, stdout=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL, text=True)
        with process.stdout:
            try:
                remaining = self._remaining(deadline, start)
                try:
                    listing, _ = process.communicate(timeout=remaining)
                except subprocess.TimeoutExpired as error:
                    raise InventoryTimeout(response) from error
                # macOS ps exits 1 with no rows if every selected process went away.
                if process.returncode and not (pids and process.returncode == 1 and not listing.strip()):
                    raise subprocess.CalledProcessError(process.returncode, COMMAND)
                self._remaining(deadline, response)
                return listing
            finally:
                if process.returncode is None:
                    self._retire("LEGACY", process)

    def _resolve_snapshot(self, listing, deadline):
        resolved = []
        unresolved = {}
        for row in listing.splitlines():
            if not row.startswith("? "):
                resolved.append(row)
                continue
            fields = row.split()
            if (len(fields) != 3 or not fields[1].isdecimal() or fields[1] == "0"
                    or not fields[2].isdecimal() or fields[1] in unresolved):
                return self._legacy_listing(deadline)
            unresolved[fields[1]] = fields[2]
        if not 0 < len(unresolved) <= MAX_SCOPED_PIDS:
            return self._legacy_listing(deadline)

        scoped = self._legacy_listing(deadline, pids=tuple(unresolved))
        rows = [row.split(None, 2) for row in scoped.splitlines()]
        if (len(rows) != len(unresolved) or any(len(row) != 3 for row in rows)
                or {tuple(row[:2]) for row in rows} != set(unresolved.items())):
            # A PID disappeared, changed owner, or was not resolved. Require a fresh complete scan.
            return self._legacy_listing(deadline)
        return "\n".join([*resolved, scoped])

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
                listing = payload.decode(locale.getpreferredencoding(False))
                if fallback:
                    listing = self._resolve_snapshot(listing, deadline)
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
