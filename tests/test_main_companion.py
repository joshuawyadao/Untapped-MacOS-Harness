"""Synthetic main-account supervision; no game, app, or network is launched."""

import json
import os
import shutil
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from harness import main_companion as companion
from harness.asar import HarnessError


def passing_preflight():
    return {"passed": True, "requests_attempted": 2, "results": [
        {"route": "accounts_account", "status": 401, "response_kind": "JSON", "body_bytes": 85, "json_object": True},
        {"route": "oauth_token", "status": 401, "response_kind": "JSON", "body_bytes": 27, "json_object": True},
    ]}


class FakeGateway:
    def __init__(self, preflight=None):
        self.value = passing_preflight() if preflight is None else preflight
        self.counts = {}
        self.failure_details = []
        self.failure_overflow = 0
        self.cleanup_complete = True
        self.key = "private-key"
        self.url = "http://127.0.0.1:12345"
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.closed = True
        return False

    def preflight(self):
        return self.value


class FakeProcess:
    pid = 9999

    def __init__(self):
        self.waits = []
        self.alive = True

    def poll(self):
        return None if self.alive else 0

    def wait(self, timeout=None):
        self.waits.append(timeout)
        raise subprocess.TimeoutExpired("synthetic", timeout)


class MainCompanionTests(unittest.TestCase):
    def test_authentication_does_not_shorten_session_to_45_seconds(self):
        process = FakeProcess()
        times = iter([0, 10, 70, 101])
        with patch.object(companion, "_events", return_value={"authenticated"}):
            reason, events = companion.supervise(process, Path("/unused"), 100,
                                                  clock=lambda: next(times))
        self.assertEqual(reason, "SESSION_LIMIT_REACHED")
        self.assertIn("authenticated", events)
        self.assertEqual(len(process.waits), 2)

    def test_mismatch_and_game_exit_stop_only_companion(self):
        process = FakeProcess()
        with patch.object(companion, "_events", return_value={"main-steam-mismatch"}):
            self.assertEqual(companion.supervise(process, Path("/unused"), 100)[0],
                             "STEAM_ACCOUNT_MISMATCH")
        with patch.object(companion, "_events", return_value=set()):
            self.assertEqual(companion.supervise(process, Path("/unused"), 100,
                                                   should_stop=lambda: "GAME_EXIT")[0], "GAME_EXIT")
        self.assertEqual(process.waits, [])

    def _run(self, gateway, *, stop="GAME_EXIT", events=None, launch_error=None,
             harvest_error=None, cleanup_error=None, order=None, ui_version=None, seed=None):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        base = Path(temp.name).resolve()
        session, prefs = base / "session", base / "prefs"
        session.mkdir(mode=0o700)
        prefs.mkdir(mode=0o700)
        (session / "signing.json").write_text("{}")
        process = FakeProcess()
        root = Path(tempfile.mkdtemp(prefix=f"uc-sts2-main-{os.getuid()}-", dir="/private/tmp"))
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        self.addCleanup(lambda: shutil.rmtree(root) if root.exists() else None)
        (root / "profile").mkdir(mode=0o700)
        launch = Mock(side_effect=launch_error) if launch_error else Mock(return_value=process)
        def cleanup(_process):
            if order is not None:
                order.append("group_cleanup")
            if cleanup_error:
                raise cleanup_error

        def harvest(*_args):
            if order is not None:
                order.append("harvest")
            if harvest_error:
                raise harvest_error
        with patch.object(companion.platform, "system", return_value="Darwin"), \
             patch.object(companion, "_target_environment", return_value={}), \
             patch.object(companion.controlled, "proposal", return_value={}), \
             patch.object(companion.cli, "_validate_launch_copy", return_value=(session, {"main_steam_guard_version": 1, "ui_assets_version": ui_version}, session / "Companion.app")), \
             patch.object(companion, "Gateway", return_value=gateway), \
             patch.object(companion, "_clone", return_value=root) as clone, \
             patch.object(companion, "_launch", launch), \
             patch.object(companion, "_events", return_value=events or set()), \
             patch.object(companion.cli, "stop_probe", side_effect=cleanup) as terminate, \
             patch.object(companion.main_preferences, "seed", seed or Mock()), \
             patch.object(companion.main_preferences, "harvest", side_effect=harvest), \
             patch.object(companion, "_diagnostic") as diagnostic:
            report = companion.run(session, prefs, target_pid=123,
                                   target_game=Path("/synthetic/game"), expected_steam_id="12345678901234567",
                                   expected_profile=0, should_stop=lambda: stop)
        return report, clone, launch, terminate, diagnostic, root

    def test_both_ui_versions_preserve_default_character_tier_seeding(self):
        for version, expected in ((None, False), (1, True), (2, True)):
            with self.subTest(version=version):
                seed = Mock()
                self._run(FakeGateway(), ui_version=version, seed=seed)
                self.assertEqual(seed.call_args.kwargs['enable_default_tiers'], expected)

    def test_preflight_failure_never_opens_app(self):
        gateway = FakeGateway({"passed": False, "requests_attempted": 0, "results": []})
        report, clone, launch, terminate, diagnostic, root = self._run(gateway)
        clone.assert_not_called()
        launch.assert_not_called()
        terminate.assert_not_called()
        self.assertFalse(report["companion_started"])
        self.assertEqual(report["reason"], "PREFLIGHT_FAILED")
        # The synthetic clone was never handed to the runner.
        (root / "profile").rmdir()
        root.rmdir()

    def test_game_exit_terminates_companion_and_removes_private_copy(self):
        report, clone, launch, terminate, diagnostic, root = self._run(FakeGateway(),
            events={"authenticated", "main-steam-verified", "reward", "overlay-show"})
        self.assertEqual(report["reason"], "GAME_EXIT")
        self.assertTrue(report["companion_terminated"])
        self.assertTrue(report["steam_account_verified"])
        self.assertTrue(report["preferences_saved"])
        self.assertFalse(root.exists())
        terminate.assert_called_once()
        self.assertNotIn("12345678901234567", json.dumps(report))

    def test_launch_failure_reports_fixed_stage_after_gateway_drain(self):
        gateway = FakeGateway()
        report, _, launch, terminate, diagnostic, root = self._run(
            gateway, launch_error=RuntimeError("secret-token private@example.test"))
        self.assertTrue(gateway.closed)
        self.assertEqual(report["reason"], "COMPANION_FAILED")
        self.assertEqual(report["failure_stage"], "LAUNCH")
        self.assertFalse(report["companion_started"])
        self.assertTrue(report["private_attempt_retained"])
        self.assertTrue(root.exists())
        self.assertNotIn("secret-token", json.dumps(report))
        terminate.assert_not_called()
        diagnostic.assert_called_once()

    def test_harvest_failure_reports_fixed_stage_after_group_cleanup(self):
        order = []
        report, _, _, terminate, diagnostic, root = self._run(
            FakeGateway(), harvest_error=RuntimeError("secret-token"), order=order)
        self.assertEqual(order, ["group_cleanup", "harvest"])
        self.assertEqual(report["failure_stage"], "HARVEST")
        self.assertFalse(report["preferences_saved"])
        self.assertTrue(report["private_attempt_retained"])
        self.assertTrue(root.exists())
        self.assertNotIn("secret-token", json.dumps(report))
        terminate.assert_called_once()
        diagnostic.assert_called_once()

    def test_cleanup_failure_does_not_harvest_live_profile(self):
        order = []
        report, _, _, terminate, _, root = self._run(
            FakeGateway(), cleanup_error=RuntimeError("secret-token"), order=order)
        self.assertEqual(order, ["group_cleanup"])
        self.assertEqual(report["reason"], "COMPANION_CLEANUP_FAILED")
        self.assertFalse(report["companion_group_cleanup_complete"])
        self.assertTrue(root.exists())
        terminate.assert_called_once()

    def test_cleanup_interrupt_is_not_reported_as_complete(self):
        report, _, _, terminate, _, root = self._run(FakeGateway(), cleanup_error=KeyboardInterrupt())
        self.assertFalse(report["companion_group_cleanup_complete"])
        self.assertEqual(report["failure_stage"], "GROUP_CLEANUP")
        self.assertTrue(report["private_attempt_retained"])
        self.assertTrue(root.exists())
        terminate.assert_called_once()

    def test_account_mismatch_never_reports_verified(self):
        report, _, _, terminate, _, root = self._run(FakeGateway(),
            events={"authenticated", "main-steam-verified", "main-steam-mismatch"})
        self.assertEqual(report["reason"], "STEAM_ACCOUNT_MISMATCH")
        self.assertFalse(report["steam_account_verified"])
        terminate.assert_called_once()
        self.assertFalse(root.exists())

    def test_exited_leader_still_cleans_owned_helper_group_before_profile_harvest(self):
        with patch.object(companion, "supervise", return_value=("COMPANION_EXITED", set())), \
             patch.object(FakeProcess, "poll", return_value=0):
            report, _, _, terminate, _, root = self._run(FakeGateway())
        terminate.assert_called_once()
        self.assertFalse(report["companion_terminated"])
        self.assertFalse(root.exists())

    def test_process_exit_status_distinguishes_quit_from_crash(self):
        for code in (0, 1, -11):
            with self.subTest(exit_code=code), patch.object(FakeProcess, "poll", return_value=code):
                report, _, _, terminate, diagnostic, root = self._run(
                    FakeGateway(), stop=None, events={"authenticated", "main-steam-verified"})
                self.assertEqual(report["companion_exit_code"], code)
                self.assertEqual(report["reason"], "COMPANION_EXITED" if code == 0 else "COMPANION_CRASHED")
                self.assertEqual(report["failure_stage"], "NONE" if code == 0 else "PROCESS_EXIT")
                self.assertEqual(root.exists(), code != 0)
                self.assertEqual(report["private_attempt_retained"], code != 0)
                self.assertTrue(report["companion_group_cleanup_complete"])
                self.assertFalse(report["companion_terminated"])
                terminate.assert_called_once()
                diagnostic.assert_called_once()

    def test_game_crash_retains_evidence_and_cleans_only_the_companion(self):
        report, _, _, terminate, diagnostic, root = self._run(
            FakeGateway(), stop="GAME_CRASHED", events={"authenticated", "main-steam-verified"})
        self.assertEqual(report["reason"], "GAME_CRASHED")
        self.assertEqual(report["failure_stage"], "GAME_PROCESS_EXIT")
        self.assertTrue(report["private_attempt_retained"])
        self.assertTrue(root.exists())
        self.assertTrue(report["companion_group_cleanup_complete"])
        terminate.assert_called_once()
        diagnostic.assert_called_once()

    def test_bad_stop_reason_fails_closed(self):
        with patch.object(companion, "_events", return_value=set()):
            with self.assertRaises(HarnessError):
                companion.supervise(FakeProcess(), Path("/unused"), 10,
                                    should_stop=lambda: "unsafe freeform text")

    def test_target_pid_must_match_exact_owned_executable(self):
        with tempfile.TemporaryDirectory() as name:
            executable = Path(name).resolve() / "game"
            executable.write_bytes(b"synthetic")
            good = SimpleNamespace(stdout=f"{os.getuid()} {executable}\n")
            with patch.object(companion.subprocess, "run", return_value=good):
                env = companion._target_environment(123, executable)
            self.assertEqual(env["UNTAPPED_HARNESS_TARGET_PID"], "123")
            bad = SimpleNamespace(stdout=f"{os.getuid()} /other/game\n")
            with patch.object(companion.subprocess, "run", return_value=bad):
                with self.assertRaises(HarnessError):
                    companion._target_environment(123, executable)

    def test_bounded_event_tail_discards_payload_and_rejects_links(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name).resolve()
            profile = root / "profile"
            profile.mkdir(mode=0o700)
            stream = profile / "events.jsonl"
            stream.write_bytes((b'{"event":"reward","token":"secret-token"}\n' * 30000)
                               + b'{"event":"main-steam-verified","account":"private@example.test"}\n')
            self.assertEqual(companion._events(root), {"reward", "main-steam-verified"})
            stream.unlink()
            outside = root / "outside"
            outside.write_text('{}')
            stream.symlink_to(outside)
            with self.assertRaises(HarnessError):
                companion._events(root)
