"""Live guard/supervisor retry contract, using fake game and companion processes."""
import contextlib
import errno
import io
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from harness import main_companion as companion, main_launcher as launcher
from harness.asar import HarnessError
from tests import test_main_launcher as launcher_fixtures


class _Clock:
    now = 0.0

    def __call__(self):
        return self.now


class _Companion:
    def __init__(self, clock, on_wait=None):
        self.clock = clock
        self.waits = []
        self.returncode = None
        self.on_wait = on_wait

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        self.waits.append(timeout)
        self.clock.now += timeout
        if self.on_wait:
            self.on_wait(self)
        raise subprocess.TimeoutExpired('fixture poll', timeout)


class InventoryRetryTests(unittest.TestCase):
    def run_session(self, steps, *, seconds=1.0, events=None, owner=None, on_wait=None):
        case = launcher_fixtures.MainLauncherTests()
        case.setUp()
        try:
            _, game, _, _, call = case.patches()
            with contextlib.redirect_stdout(io.StringIO()):
                launcher.start(approved=True, cloud_confirmed=True, account_confirmed=True,
                    confirm_steam=lambda: None, seconds=None, should_stop=owner)
            arguments = call.call_args.kwargs
            expected = arguments['target_game']
            trace = arguments['diagnostics']
            sequence = iter(steps)
            clock = _Clock()
            process = _Companion(clock, (lambda p: on_wait(p, game)) if on_wait else None)

            def inventory():
                step = next(sequence, 'match')
                if isinstance(step, BaseException):
                    raise step
                if step == 'wrong_user':
                    return [(game.pid, os.getuid()+1, str(expected), False)]
                if step == 'wrong_game':
                    return [(game.pid, os.getuid(), '/different/Slay the Spire 2', False)]
                if step == 'no_game':
                    return []
                return [(game.pid, os.getuid(), str(expected), False)]

            extra = {}
            if 'retry_should_stop' in arguments:
                extra['retry_should_stop'] = arguments['retry_should_stop']
            with patch.object(launcher, '_inventory', side_effect=inventory) as called, \
                 patch.object(launcher.os, 'getpgid', return_value=game.pid), \
                 patch.object(companion, '_events', side_effect=events,
                              return_value=set()):
                error = None
                reason = None
                try:
                    reason, _ = companion.supervise(process, Path('/unused'), seconds,
                        should_stop=arguments['should_stop'], diagnostics=trace, clock=clock, **extra)
                except Exception as exc:
                    error = exc
                count = called.call_count
            game.kill.assert_not_called()
            game.terminate.assert_not_called()
            return SimpleNamespace(reason=reason, error=error, diagnostic=trace.snapshot(),
                                   attempts=count, waits=process.waits, elapsed=clock.now)
        finally:
            case.doCleanups()

    @staticmethod
    def timeout():
        return subprocess.TimeoutExpired('private-fixture-command', 2,
            output=b'private-fixture-output', stderr=b'private-fixture-stderr')

    def test_timeout_then_fresh_success_keeps_session_alive(self):
        result = self.run_session([self.timeout(), 'match'])
        self.assertIsNone(result.error)
        self.assertEqual(result.reason, 'SESSION_LIMIT_REACHED')
        self.assertGreaterEqual(result.attempts, 2)
        self.assertIsNone(result.diagnostic['failure'])
        self.assertEqual(result.diagnostic['inventory_retry'],
            {'timeouts': 1, 'retries_scheduled': 1, 'recoveries': 1, 'exhaustions': 0})
        self.assertAlmostEqual(result.elapsed, 1.0)
        self.assertNotIn('private-fixture', repr(result.diagnostic))

    def test_three_consecutive_timeouts_exhaust_without_fourth_attempt(self):
        errors = [self.timeout() for _ in range(4)]
        result = self.run_session(errors)
        self.assertIs(result.error, errors[2])
        self.assertEqual(result.attempts, 3)
        self.assertAlmostEqual(result.elapsed, .5)
        self.assertEqual(result.diagnostic['failure'],
            {'check': 'GAME_PROCESS_INVENTORY', 'category': 'TIMEOUT'})
        self.assertEqual(result.diagnostic['inventory_retry'],
            {'timeouts': 3, 'retries_scheduled': 2, 'recoveries': 0, 'exhaustions': 1})

    def test_budget_resets_only_after_successful_fresh_identity_check(self):
        result = self.run_session([self.timeout(), self.timeout(), 'match',
                                   self.timeout(), self.timeout(), 'match'], seconds=2)
        self.assertIsNone(result.error)
        self.assertEqual(result.reason, 'SESSION_LIMIT_REACHED')
        self.assertEqual(result.diagnostic['inventory_retry'],
            {'timeouts': 4, 'retries_scheduled': 4, 'recoveries': 2, 'exhaustions': 0})
        self.assertIsNone(result.diagnostic['failure'])

    def test_confirmed_game_mismatch_stops_without_retry(self):
        for mismatch in ('wrong_user', 'wrong_game', 'no_game'):
            with self.subTest(mismatch=mismatch):
                result = self.run_session([mismatch])
                self.assertEqual(result.reason, 'TARGET_CONFLICT')
                self.assertEqual(result.attempts, 1)
                self.assertEqual(result.waits, [])
                self.assertNotIn('inventory_retry', result.diagnostic)

    def test_confirmed_mismatch_after_timeout_gets_no_additional_attempt(self):
        for mismatch in ('wrong_user', 'wrong_game', 'no_game'):
            with self.subTest(mismatch=mismatch):
                result = self.run_session([self.timeout(), mismatch])
                self.assertIsNone(result.error)
                self.assertEqual(result.reason, 'TARGET_CONFLICT')
                self.assertEqual(result.attempts, 2)
                self.assertAlmostEqual(result.elapsed, .25)
                self.assertEqual(result.diagnostic['inventory_retry']['recoveries'], 0)

    def test_account_mismatch_bypasses_inventory_and_retry_backoff(self):
        result = self.run_session(['match'], events=lambda *_: {'main-steam-mismatch'})
        self.assertEqual(result.reason, 'STEAM_ACCOUNT_MISMATCH')
        self.assertEqual(result.attempts, 0)
        self.assertEqual(result.waits, [])
        calls = 0

        def events(*_):
            nonlocal calls
            calls += 1
            return set() if calls == 1 else {'main-steam-mismatch'}
        result = self.run_session([self.timeout(), 'match'], events=events)
        self.assertEqual(result.reason, 'STEAM_ACCOUNT_MISMATCH')
        self.assertEqual(result.attempts, 1)
        self.assertEqual(result.waits, [])

    def test_game_companion_exit_and_owner_stop_abort_waiting_retry(self):
        def game_exit(_companion, game): game.poll.return_value = 0
        def game_crash(_companion, game): game.poll.return_value = -11
        def companion_exit(process, _game): process.returncode = 0
        for change, expected in ((game_exit, 'GAME_EXIT'), (game_crash, 'GAME_CRASHED'),
                                 (companion_exit, 'COMPANION_EXITED')):
            with self.subTest(expected=expected):
                result = self.run_session([self.timeout(), 'match'], on_wait=change)
                self.assertEqual(result.reason, expected)
                self.assertEqual(result.attempts, 1)
                self.assertLessEqual(result.elapsed, .05)
        state = {'stop': False}
        result = self.run_session([self.timeout(), 'match'],
            owner=lambda: 'OWNER_STOP' if state['stop'] else None,
            on_wait=lambda *_: state.update(stop=True))
        self.assertEqual(result.reason, 'OWNER_STOP')
        self.assertEqual(result.attempts, 1)
        self.assertLessEqual(result.elapsed, .05)

    def test_finite_deadline_aborts_before_retry_attempt(self):
        result = self.run_session([self.timeout(), 'match'], seconds=.1)
        self.assertEqual(result.reason, 'SESSION_LIMIT_REACHED')
        self.assertEqual(result.attempts, 1)
        self.assertAlmostEqual(result.elapsed, .1)

    def test_non_timeout_inventory_errors_are_not_retried(self):
        for error in (HarnessError('private-fixture'), PermissionError(errno.EACCES, 'private-fixture'),
                      subprocess.CalledProcessError(1, 'private-fixture')):
            with self.subTest(error=type(error).__name__):
                result = self.run_session([error, 'match'])
                if isinstance(error, subprocess.CalledProcessError): self.assertIs(result.error, error)
                else: self.assertEqual(result.reason, 'TARGET_CONFLICT')
                self.assertEqual(result.attempts, 1)
                self.assertEqual(result.waits, [])
                self.assertNotIn('inventory_retry', result.diagnostic)

    def test_other_check_timeouts_are_not_inventory_retries(self):
        calls = 0

        def owner():
            nonlocal calls
            calls += 1
            if calls > 2: raise self.timeout()
            return None
        result = self.run_session(['match'], owner=owner)
        self.assertIsInstance(result.error, subprocess.TimeoutExpired)
        self.assertEqual(result.diagnostic['failure']['check'], 'OWNER_STOP_CHECK')
        self.assertEqual(result.attempts, 1)
        self.assertNotIn('inventory_retry', result.diagnostic)


if __name__ == '__main__':
    unittest.main()
