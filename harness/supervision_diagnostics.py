"""Small, allowlisted diagnostics for the desktop supervision loop.

No exception text or process details are retained. This module is safe to use
around checks that may encounter private game or account data.
"""

import math
import subprocess
import time

from .asar import HarnessError


CHECKS = frozenset({
    "EVENT_READ", "GAME_GUARD", "GAME_PROCESS_INVENTORY",
    "GAME_PROCESS_GROUP", "GAME_PROCESS_POLL", "COMPANION_POLL",
    "COMPANION_WAIT", "SUPERVISION_CLOCK", "OWNER_STOP_CHECK",
    "STOP_RESULT_VALIDATE", "GROUP_CLEANUP", "FINAL_EVENT_READ",
    "PREFERENCE_HARVEST", "LOGIN_BRIDGE_CLEANUP", "ATTEMPT_CLEANUP",
    "GATEWAY_CLEANUP",
})

CATEGORIES = frozenset({
    "TIMEOUT", "PERMISSION_DENIED", "NOT_FOUND", "OS_ERROR",
    "PROCESS_ERROR", "CHECK_REJECTED", "INVALID_RESULT", "INTERRUPTED",
    "UNEXPECTED_ERROR",
})

_CHECK_LABELS = {
    "EVENT_READ": "event reading",
    "GAME_GUARD": "game safety check",
    "GAME_PROCESS_INVENTORY": "game process inventory",
    "GAME_PROCESS_GROUP": "game process group check",
    "GAME_PROCESS_POLL": "game process check",
    "COMPANION_POLL": "companion process check",
    "COMPANION_WAIT": "companion exit wait",
    "SUPERVISION_CLOCK": "supervision clock check",
    "OWNER_STOP_CHECK": "launcher stop check",
    "STOP_RESULT_VALIDATE": "stop result validation",
    "GROUP_CLEANUP": "process group cleanup",
    "FINAL_EVENT_READ": "final event reading",
    "PREFERENCE_HARVEST": "preference saving",
    "LOGIN_BRIDGE_CLEANUP": "login bridge cleanup",
    "ATTEMPT_CLEANUP": "attempt cleanup",
    "GATEWAY_CLEANUP": "gateway cleanup",
}

_CATEGORY_LABELS = {
    "TIMEOUT": "timeout",
    "PERMISSION_DENIED": "permission denied",
    "NOT_FOUND": "item not found",
    "OS_ERROR": "system error",
    "PROCESS_ERROR": "process error",
    "CHECK_REJECTED": "check rejected",
    "INVALID_RESULT": "invalid result",
    "INTERRUPTED": "interrupted",
    "UNEXPECTED_ERROR": "unexpected error",
}

_MAX_ATTEMPTS = 2**31 - 1


def _category(exc):
    if isinstance(exc, (KeyboardInterrupt, InterruptedError)):
        return "INTERRUPTED"
    if isinstance(exc, (TimeoutError, subprocess.TimeoutExpired)):
        return "TIMEOUT"
    if isinstance(exc, PermissionError):
        return "PERMISSION_DENIED"
    if isinstance(exc, FileNotFoundError):
        return "NOT_FOUND"
    if isinstance(exc, subprocess.SubprocessError):
        return "PROCESS_ERROR"
    if isinstance(exc, OSError):
        return "OS_ERROR"
    if isinstance(exc, HarnessError):
        return "CHECK_REJECTED"
    if isinstance(exc, (TypeError, ValueError)):
        return "INVALID_RESULT"
    return "UNEXPECTED_ERROR"


def failure_record(check, exc):
    """Classify a failed allowlisted check without serializing exception content."""
    if not isinstance(check, str) or check not in CHECKS:
        raise ValueError("Unknown supervision check")

    selected = exc
    seen = set()
    for _ in range(4):
        if not isinstance(selected, BaseException) or id(selected) in seen:
            break
        seen.add(id(selected))
        category = _category(selected)
        if category not in ("CHECK_REJECTED", "INVALID_RESULT", "UNEXPECTED_ERROR"):
            break
        try:
            next_exc = selected.__cause__
        except BaseException:
            next_exc = None
        if next_exc is None:
            try:
                next_exc = selected.__context__
            except BaseException:
                next_exc = None
        if not isinstance(next_exc, BaseException) or id(next_exc) in seen:
            break
        selected = next_exc

    category = _category(selected)
    result = {"check": check, "category": category}
    if isinstance(selected, OSError):
        try:
            code = selected.errno
        except BaseException:
            code = None
        if type(code) is int and 1 <= code <= 4095:
            result["errno"] = code
    if isinstance(selected, subprocess.CalledProcessError):
        try:
            code = selected.returncode
        except BaseException:
            code = None
        if type(code) is int and -255 <= code <= 255:
            result["returncode"] = code
    return result


class SupervisionDiagnostics:
    """Retain only the first failure and bounded progress counters."""

    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.checks_attempted = 0
        self.last_check = None
        self.last_completed_check = None
        self.failure = None
        self._last_check_elapsed_ms = None
        self._check_sequence = 0
        self._inventory_timeouts = 0
        self._inventory_retries = 0
        self._inventory_recoveries = 0
        self._inventory_exhaustions = 0

    def record_inventory_timeout(self, *, retrying: bool) -> bool:
        """Account for a timeout just captured from the inventory check.

        A retry makes that first failure provisional, so a later failure can be
        reported accurately. Other failures are never cleared here.
        """
        if type(retrying) is not bool or self.failure is None:
            return False
        if (self.failure.get("check") != "GAME_PROCESS_INVENTORY"
                or self.failure.get("category") != "TIMEOUT"):
            return False
        self._inventory_timeouts = min(_MAX_ATTEMPTS, self._inventory_timeouts + 1)
        if retrying:
            self._inventory_retries = min(_MAX_ATTEMPTS, self._inventory_retries + 1)
            self.failure = None
        else:
            self._inventory_exhaustions = min(_MAX_ATTEMPTS, self._inventory_exhaustions + 1)
        return True

    def record_inventory_recovery(self) -> None:
        """Record a successful guard after one or more inventory timeouts."""
        self._inventory_recoveries = min(_MAX_ATTEMPTS, self._inventory_recoveries + 1)

    def _safe_clock(self):
        try:
            value = self.clock()
            if type(value) not in (int, float) or not math.isfinite(value):
                return None
            return float(value)
        except BaseException:
            return None

    def call(self, check, action, *args, **kwargs):
        if not isinstance(check, str) or check not in CHECKS:
            raise ValueError("Unknown supervision check")
        self.checks_attempted = min(_MAX_ATTEMPTS, self.checks_attempted + 1)
        self._check_sequence = (self._check_sequence + 1) % (2**63)
        sequence = self._check_sequence
        self.last_check = check
        self._last_check_elapsed_ms = None
        start = self._safe_clock()
        try:
            result = action(*args, **kwargs)
        except BaseException as exc:
            if self.failure is None:
                try:
                    self.failure = failure_record(check, exc)
                except BaseException:
                    self.failure = {"check": check, "category": "UNEXPECTED_ERROR"}
            raise
        else:
            self.last_completed_check = check
            return result
        finally:
            end = self._safe_clock()
            if sequence == self._check_sequence and start is not None and end is not None:
                milliseconds = (end - start) * 1000
                if math.isfinite(milliseconds) and 0 <= milliseconds <= _MAX_ATTEMPTS:
                    self._last_check_elapsed_ms = int(milliseconds)

    def snapshot(self):
        result = {
            "schema": 1,
            "checks_attempted": self.checks_attempted,
            "last_check": self.last_check,
            "last_completed_check": self.last_completed_check,
            "failure": dict(self.failure) if self.failure is not None else None,
        }
        if self._last_check_elapsed_ms is not None:
            result["last_check_elapsed_ms"] = self._last_check_elapsed_ms
        if self._inventory_timeouts:
            result["inventory_retry"] = {
                "timeouts": self._inventory_timeouts,
                "retries_scheduled": self._inventory_retries,
                "recoveries": self._inventory_recoveries,
                "exhaustions": self._inventory_exhaustions,
            }
        return result


def failure_message(diagnostic):
    """Return a fixed, friendly message for a valid diagnostic failure."""
    if not isinstance(diagnostic, dict):
        return None
    failure = diagnostic.get("failure")
    if not isinstance(failure, dict):
        return None
    check = failure.get("check")
    category = failure.get("category")
    if (not isinstance(check, str) or not isinstance(category, str)
            or check not in _CHECK_LABELS or category not in _CATEGORY_LABELS):
        return None
    return "Supervision stopped during %s (%s)." % (
        _CHECK_LABELS[check], _CATEGORY_LABELS[category]
    )
