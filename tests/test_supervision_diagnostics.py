import errno
import subprocess
import unittest
from unittest.mock import Mock

from harness.asar import HarnessError
from harness.live_inventory import InventoryTimeout
from harness.supervision_diagnostics import (
    CATEGORIES,
    CHECKS,
    SupervisionDiagnostics,
    failure_message,
    failure_record,
)


class SupervisionDiagnosticTests(unittest.TestCase):
    def test_inventory_timeout_phase_survives_recovery_with_allowlisted_data_only(self):
        diagnostic = SupervisionDiagnostics(clock=lambda: 1.0)
        error = InventoryTimeout("LEGACY_RESPONSE")
        error.stdout = "private process listing"
        with self.assertRaises(InventoryTimeout):
            diagnostic.call("GAME_PROCESS_INVENTORY", Mock(side_effect=error))
        self.assertEqual(diagnostic.snapshot()["failure"], {
            "check": "GAME_PROCESS_INVENTORY", "category": "TIMEOUT", "phase": "LEGACY_RESPONSE",
        })
        self.assertTrue(diagnostic.record_inventory_timeout(retrying=True))
        diagnostic.record_inventory_recovery()
        snapshot = diagnostic.snapshot()
        self.assertIsNone(snapshot["failure"])
        self.assertEqual(snapshot["inventory_retry"]["last_timeout_phase"], "LEGACY_RESPONSE")
        self.assertNotIn("private process listing", repr(snapshot))
        self.assertNotIn("phase", failure_record("GAME_PROCESS_INVENTORY", InventoryTimeout("private value")))

    def test_nested_failure_keeps_inner_check_and_original_exception(self):
        diagnostic = SupervisionDiagnostics(clock=lambda: 1.0)
        error = PermissionError(errno.EACCES, "private account token", "/secret/path")

        def inner():
            raise error

        with self.assertRaises(PermissionError) as caught:
            diagnostic.call(
                "GAME_GUARD",
                lambda: diagnostic.call("GAME_PROCESS_INVENTORY", inner),
            )
        self.assertIs(caught.exception, error)
        snapshot = diagnostic.snapshot()
        self.assertEqual(snapshot["checks_attempted"], 2)
        self.assertEqual(snapshot["last_check"], "GAME_PROCESS_INVENTORY")
        self.assertIsNone(snapshot["last_completed_check"])
        self.assertEqual(snapshot["failure"], {
            "check": "GAME_PROCESS_INVENTORY",
            "category": "PERMISSION_DENIED",
            "errno": errno.EACCES,
        })
        self.assertNotIn("private account token", repr(snapshot))
        self.assertNotIn("/secret/path", repr(snapshot))

    def test_cause_and_context_are_bounded_and_classified(self):
        wrapped = HarnessError("secret wrapper")
        wrapped.__cause__ = subprocess.TimeoutExpired("secret command", 7)
        self.assertEqual(failure_record("COMPANION_WAIT", wrapped), {
            "check": "COMPANION_WAIT", "category": "TIMEOUT",
        })
        generic = RuntimeError("secret")
        generic.__context__ = FileNotFoundError(errno.ENOENT, "secret", "/secret")
        self.assertEqual(failure_record("EVENT_READ", generic)["category"], "NOT_FOUND")
        generic.__context__.__context__ = generic
        self.assertEqual(failure_record("EVENT_READ", generic)["category"], "NOT_FOUND")

    def test_private_exception_attributes_and_numeric_bounds(self):
        class AccountTokenMustNeverAppear(HarnessError):
            token = "private-token"
            filename = "/private/account"

        record = failure_record("OWNER_STOP_CHECK", AccountTokenMustNeverAppear("secret"))
        self.assertEqual(record, {"check": "OWNER_STOP_CHECK", "category": "CHECK_REJECTED"})
        self.assertNotIn("AccountToken", repr(record))
        self.assertEqual(failure_record("GAME_GUARD", OSError(9000, "secret")), {
            "check": "GAME_GUARD", "category": "OS_ERROR",
        })
        self.assertEqual(failure_record("GAME_GUARD", subprocess.CalledProcessError(
            999, ["secret", "command"], output="private stdout", stderr="private stderr"
        )), {"check": "GAME_GUARD", "category": "PROCESS_ERROR"})
        self.assertEqual(failure_record("GAME_GUARD", subprocess.CalledProcessError(-9, "secret")), {
            "check": "GAME_GUARD", "category": "PROCESS_ERROR", "returncode": -9,
        })
        self.assertEqual(failure_record("GAME_GUARD", TypeError("secret"))["category"], "INVALID_RESULT")
        self.assertEqual(failure_record("GAME_GUARD", KeyboardInterrupt())["category"], "INTERRUPTED")
        self.assertEqual(failure_record("GAME_GUARD", InterruptedError())["category"], "INTERRUPTED")

    def test_unknown_check_and_hostile_report_never_echo_fields(self):
        with self.assertRaisesRegex(ValueError, "Unknown supervision check"):
            failure_record("secret-token-check", RuntimeError("secret"))
        self.assertIsNone(failure_message({"failure": {
            "check": "secret-token-check", "category": "TIMEOUT", "token": "secret"
        }}))
        self.assertIsNone(failure_message({"failure": {
            "check": "EVENT_READ", "category": "secret-token-category"
        }}))
        self.assertIsNone(failure_message({"failure": "secret"}))
        self.assertIsNone(failure_message({"failure": {
            "check": ["EVENT_READ"], "category": {"TIMEOUT": True},
        }}))
        self.assertEqual(failure_message({"failure": {
            "check": "GAME_PROCESS_INVENTORY", "category": "TIMEOUT",
            "token": "secret", "message": "private-token",
        }}), "Supervision stopped during game process inventory (timeout).")
        self.assertEqual(set(CHECKS), set(__import__(
            "harness.supervision_diagnostics", fromlist=["_CHECK_LABELS"]
        )._CHECK_LABELS))
        self.assertEqual(set(CATEGORIES), set(__import__(
            "harness.supervision_diagnostics", fromlist=["_CATEGORY_LABELS"]
        )._CATEGORY_LABELS))

    def test_bounded_snapshot_after_many_calls_and_broken_clock(self):
        calls = 0

        def bad_clock():
            nonlocal calls
            calls += 1
            raise RuntimeError("private clock data")

        diagnostic = SupervisionDiagnostics(clock=bad_clock)
        for _ in range(2000):
            self.assertEqual(diagnostic.call("GAME_PROCESS_POLL", lambda: 5), 5)
        snapshot = diagnostic.snapshot()
        self.assertEqual(snapshot, {
            "schema": 1,
            "checks_attempted": 2000,
            "last_check": "GAME_PROCESS_POLL",
            "last_completed_check": "GAME_PROCESS_POLL",
            "failure": None,
        })
        self.assertGreater(calls, 0)
        self.assertLess(len(repr(diagnostic.__dict__)), 1000)

    def test_first_failure_survives_later_failure(self):
        diagnostic = SupervisionDiagnostics()
        for check, error in [
            ("COMPANION_POLL", TimeoutError("private")),
            ("GROUP_CLEANUP", OSError(errno.EIO, "private")),
        ]:
            with self.assertRaises(type(error)):
                diagnostic.call(check, lambda error=error: (_ for _ in ()).throw(error))
        self.assertEqual(diagnostic.snapshot()["failure"], {
            "check": "COMPANION_POLL", "category": "TIMEOUT",
        })

    def test_hostile_exception_chain_getters_preserve_original_failure(self):
        class HostileException(RuntimeError):
            def __getattribute__(self, name):
                if name in ("__cause__", "__context__"):
                    raise RuntimeError("private getter data")
                return super().__getattribute__(name)

        error = HostileException("private message")
        diagnostic = SupervisionDiagnostics()
        with self.assertRaises(HostileException) as caught:
            diagnostic.call("GAME_GUARD", lambda: (_ for _ in ()).throw(error))
        self.assertIs(caught.exception, error)
        self.assertEqual(diagnostic.snapshot()["failure"], {
            "check": "GAME_GUARD", "category": "UNEXPECTED_ERROR",
        })
        self.assertNotIn("private", repr(diagnostic.snapshot()))

    def test_last_check_duration_is_reset_when_clock_breaks(self):
        times = iter((1.0, 1.125))
        diagnostic = SupervisionDiagnostics(clock=lambda: next(times))
        diagnostic.call("EVENT_READ", lambda: None)
        self.assertEqual(diagnostic.snapshot()["last_check_elapsed_ms"], 125)
        diagnostic.call("GAME_GUARD", lambda: None)
        self.assertNotIn("last_check_elapsed_ms", diagnostic.snapshot())

    def test_nested_outer_duration_does_not_replace_inner_duration(self):
        times = iter((0.0, 1.0, 2.0, 10.0))
        diagnostic = SupervisionDiagnostics(clock=lambda: next(times))
        diagnostic.call("GAME_GUARD", lambda: diagnostic.call("EVENT_READ", lambda: None))
        snapshot = diagnostic.snapshot()
        self.assertEqual(snapshot["last_check"], "EVENT_READ")
        self.assertEqual(snapshot["last_check_elapsed_ms"], 1000)

    def test_inventory_retry_clears_only_provisional_timeout(self):
        diagnostic = SupervisionDiagnostics(clock=lambda: 1.0)
        self.assertNotIn("inventory_retry", diagnostic.snapshot())
        with self.assertRaises(TimeoutError):
            diagnostic.call("GAME_PROCESS_INVENTORY", lambda: (_ for _ in ()).throw(
                TimeoutError("private process data")
            ))
        self.assertFalse(diagnostic.record_inventory_timeout(retrying="yes"))
        self.assertEqual(diagnostic.snapshot()["failure"]["category"], "TIMEOUT")
        self.assertNotIn("inventory_retry", diagnostic.snapshot())
        self.assertTrue(diagnostic.record_inventory_timeout(retrying=True))
        diagnostic.record_inventory_recovery()
        snapshot = diagnostic.snapshot()
        self.assertIsNone(snapshot["failure"])
        self.assertEqual(snapshot["inventory_retry"], {
            "timeouts": 1, "retries_scheduled": 1, "recoveries": 1, "exhaustions": 0,
        })
        self.assertNotIn("private", repr(snapshot))

    def test_inventory_exhaustion_keeps_failure_and_rejects_other_failures(self):
        diagnostic = SupervisionDiagnostics()
        with self.assertRaises(TimeoutError):
            diagnostic.call("GAME_PROCESS_INVENTORY", lambda: (_ for _ in ()).throw(
                TimeoutError("private")
            ))
        self.assertTrue(diagnostic.record_inventory_timeout(retrying=False))
        self.assertEqual(diagnostic.snapshot()["failure"], {
            "check": "GAME_PROCESS_INVENTORY", "category": "TIMEOUT",
        })
        self.assertEqual(diagnostic.snapshot()["inventory_retry"]["exhaustions"], 1)
        other = SupervisionDiagnostics()
        with self.assertRaises(TimeoutError):
            other.call("COMPANION_POLL", lambda: (_ for _ in ()).throw(TimeoutError()))
        self.assertFalse(other.record_inventory_timeout(retrying=True))
        self.assertNotIn("inventory_retry", other.snapshot())
        not_timeout = SupervisionDiagnostics()
        with self.assertRaises(PermissionError):
            not_timeout.call("GAME_PROCESS_INVENTORY", lambda: (_ for _ in ()).throw(
                PermissionError("private")
            ))
        self.assertFalse(not_timeout.record_inventory_timeout(retrying=True))
        self.assertEqual(not_timeout.snapshot()["failure"]["category"], "PERMISSION_DENIED")

    def test_multiple_inventory_timeout_sequences_and_counter_bounds(self):
        diagnostic = SupervisionDiagnostics()
        for _ in range(2):
            with self.assertRaises(TimeoutError):
                diagnostic.call("GAME_PROCESS_INVENTORY", lambda: (_ for _ in ()).throw(
                    TimeoutError("private")
                ))
            self.assertTrue(diagnostic.record_inventory_timeout(retrying=True))
        diagnostic.record_inventory_recovery()
        with self.assertRaises(TimeoutError):
            diagnostic.call("GAME_PROCESS_INVENTORY", lambda: (_ for _ in ()).throw(
                TimeoutError("private")
            ))
        self.assertTrue(diagnostic.record_inventory_timeout(retrying=False))
        self.assertEqual(diagnostic.snapshot()["inventory_retry"], {
            "timeouts": 3, "retries_scheduled": 2, "recoveries": 1, "exhaustions": 1,
        })
        from harness import supervision_diagnostics as module
        diagnostic._inventory_timeouts = module._MAX_ATTEMPTS
        diagnostic._inventory_exhaustions = module._MAX_ATTEMPTS
        self.assertTrue(diagnostic.record_inventory_timeout(retrying=False))
        self.assertEqual(diagnostic.snapshot()["inventory_retry"]["timeouts"], module._MAX_ATTEMPTS)
        self.assertEqual(diagnostic.snapshot()["inventory_retry"]["exhaustions"], module._MAX_ATTEMPTS)


if __name__ == "__main__":
    unittest.main()
