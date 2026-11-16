import errno
import subprocess
import unittest

from harness.asar import HarnessError
from harness.supervision_diagnostics import (
    CATEGORIES,
    CHECKS,
    SupervisionDiagnostics,
    failure_message,
    failure_record,
)


class SupervisionDiagnosticTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
