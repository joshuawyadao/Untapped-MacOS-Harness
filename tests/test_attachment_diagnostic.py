"""Portable contracts for the opt-in original-process attachment experiment."""
import io
import json
import os
import plistlib
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from harness.asar import HarnessError
from harness import attachment_diagnostic as diagnostic


class AttachmentClassificationTests(unittest.TestCase):
    def matrix(self, success):
        return [
            {"get_task_allow": target, "outer_sandbox": sandboxed,
             "acquired": success[target, sandboxed],
             "kern_return": 0 if success[target, sandboxed] else 5}
            for target in (False, True) for sandboxed in (False, True)
        ]

    def test_entitlement_and_outer_policy_are_distinguished(self):
        rows = self.matrix({(False, False): False, (False, True): False,
                            (True, False): True, (True, True): True})
        self.assertEqual(diagnostic.classify(rows), "TARGET_ENTITLEMENT_DISTINGUISHES_FIXTURES")
        rows[-1].update(acquired=False, kern_return=5)
        self.assertEqual(diagnostic.classify(rows), "OUTER_POLICY_BLOCKS_ENTITLED_FIXTURE")
        rows[2].update(acquired=False, kern_return=5)
        self.assertEqual(diagnostic.classify(rows), "INCONCLUSIVE")

    def test_rejects_missing_duplicate_or_inconsistent_native_rows(self):
        rows = self.matrix({(t, s): False for t in (False, True) for s in (False, True)})
        for invalid in (rows[:-1], rows + rows[:1],
                        [dict(rows[0], get_task_allow=1), *rows[1:]],
                        [dict(rows[0], acquired=True), *rows[1:]],
                        [dict(rows[0], kern_return=True), *rows[1:]]):
            with self.subTest(invalid=invalid), self.assertRaises(HarnessError):
                diagnostic.classify(invalid)


class CommandAndSigningTests(unittest.TestCase):
    def test_command_rejects_timeout_and_nonzero_status(self):
        with patch.object(diagnostic.subprocess, "run", side_effect=subprocess.TimeoutExpired("x", 2)):
            with self.assertRaisesRegex(HarnessError, "timed out"):
                diagnostic._command(["x"], {}, "/private/tmp", timeout=2)
        with patch.object(diagnostic.subprocess, "run", return_value=SimpleNamespace(
                returncode=71, stderr="sandbox denied", stdout="")):
            with self.assertRaisesRegex(HarnessError, "sandbox denied"):
                diagnostic._command(["x"], {}, "/private/tmp")

    def test_build_checks_exact_entitlements_and_hardened_signature(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            commands = []
            requested = {**diagnostic.GAME_ENTITLEMENTS, diagnostic.GET_TASK_ALLOW: True}

            def command(args, environment, cwd, timeout=30):
                commands.append(args)
                if args[0] == "/usr/bin/clang":
                    Path(args[-1]).write_bytes(b"original fixture only")
                if "--entitlements" in args and "-d" in args:
                    return SimpleNamespace(stdout=plistlib.dumps(requested).decode(), stderr="")
                if "-dvv" in args:
                    return SimpleNamespace(stdout="", stderr="flags=0x10002(adhoc,runtime)\nSignature=adhoc")
                return SimpleNamespace(stdout="", stderr="")

            with patch.object(diagnostic, "_command", side_effect=command):
                binary = diagnostic._build(root, "attachment_target.c", "target-1", requested, {})
            self.assertEqual(binary, root / "target-1")
            self.assertEqual(plistlib.loads((root / "target-1.plist").read_bytes()), requested)
            self.assertEqual(commands[0][0], "/usr/bin/clang")
            self.assertEqual(Path(commands[0][5]).name, "attachment_target.c")
            self.assertEqual(commands[1][:6], ["/usr/bin/codesign", "--force", "--sign", "-", "--options", "runtime"])
            self.assertIn("--verify", commands[2])

            def bad_command(args, environment, cwd, timeout=30):
                if args[0] == "/usr/bin/clang":
                    Path(args[-1]).write_bytes(b"fixture")
                if "--entitlements" in args and "-d" in args:
                    return SimpleNamespace(stdout=plistlib.dumps({}).decode(), stderr="")
                return SimpleNamespace(stdout="", stderr="")

            with patch.object(diagnostic, "_command", side_effect=bad_command):
                with self.assertRaisesRegex(HarnessError, "entitlements differ"):
                    diagnostic._build(root, "attachment_target.c", "target-bad", requested, {})


class RunnerCleanupTests(unittest.TestCase):
    def exercise_failure(self, inspector_result):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            process = SimpleNamespace(pid=12345, stdout=io.BytesIO(), ended=False)
            process.poll = lambda: 0 if process.ended else None
            commands = []

            def build(directory, source, name, entitlements, environment):
                binary = directory / name
                binary.write_bytes(b"fixture")
                return binary

            def command(args, environment, cwd, timeout=30):
                commands.append(args)
                if isinstance(inspector_result, Exception):
                    raise inspector_result
                return SimpleNamespace(stdout=json.dumps(inspector_result))

            def stop(child):
                child.ended = True

            with patch.object(diagnostic.platform, "system", return_value="Darwin"), \
                 patch.object(diagnostic.tempfile, "mkdtemp", return_value=str(root)), \
                 patch.object(diagnostic, "_build", side_effect=build), \
                 patch.object(diagnostic, "sandbox_profile", return_value="original policy"), \
                 patch.object(diagnostic.subprocess, "Popen", return_value=process), \
                 patch.object(diagnostic, "_ready"), \
                 patch.object(diagnostic, "_command", side_effect=command), \
                 patch.object(diagnostic, "stop_probe", side_effect=stop):
                with self.assertRaises(HarnessError):
                    diagnostic.run()
            self.assertTrue(process.ended)
            report = json.loads((root / "report.json").read_text())
            self.assertEqual(report["conclusion"], "EXPERIMENT_FAILED")
            self.assertTrue(report["targets_stopped"])
            self.assertTrue(report["game_or_companion_modified"] is False)
            return commands

    @unittest.skipIf(os.getuid() == 0, "diagnostic intentionally refuses root")
    def test_runs_exact_four_cells_and_only_its_own_targets(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            processes = []
            commands = []
            built = []

            def build(directory, source, name, entitlements, environment):
                binary = directory / name
                binary.write_bytes(b"original fixture")
                built.append((name, dict(entitlements)))
                return binary

            def start(args, **kwargs):
                process = SimpleNamespace(pid=12000 + len(processes), stdout=io.BytesIO(), ended=False)
                process.poll = lambda p=process: 0 if p.ended else None
                processes.append(process)
                return process

            def inspect(args, environment, cwd, timeout=30):
                commands.append(args)
                pid = int(args[-2])
                return SimpleNamespace(stdout=json.dumps({"pid": pid, "uid": os.getuid(),
                    "kern_return": 0 if pid == 12001 else 5,
                    "acquired": pid == 12001}))

            with patch.object(diagnostic.platform, "system", return_value="Darwin"), \
                 patch.object(diagnostic.tempfile, "mkdtemp", return_value=str(root)), \
                 patch.object(diagnostic, "_build", side_effect=build), \
                 patch.object(diagnostic, "sandbox_profile", return_value="exact outer policy"), \
                 patch.object(diagnostic.subprocess, "Popen", side_effect=start), \
                 patch.object(diagnostic, "_ready"), \
                 patch.object(diagnostic, "_command", side_effect=inspect), \
                 patch.object(diagnostic, "stop_probe", side_effect=lambda p: setattr(p, "ended", True)):
                report = diagnostic.run()
            self.assertEqual(report["conclusion"], "TARGET_ENTITLEMENT_DISTINGUISHES_FIXTURES")
            self.assertTrue(report["targets_stopped"])
            self.assertEqual(len(commands), 4)
            self.assertEqual([command[0] == "/usr/bin/sandbox-exec" for command in commands],
                             [False, True, False, True])
            for command in commands:
                self.assertIn(command[-2], ("12000", "12001"))
                self.assertEqual(command[-1], str(root / ("target-0" if command[-2] == "12000" else "target-1")))
            self.assertEqual(built[0][1], diagnostic.GAME_ENTITLEMENTS)
            self.assertEqual(built[1][1], {**diagnostic.GAME_ENTITLEMENTS, diagnostic.GET_TASK_ALLOW: True})
            self.assertEqual(built[2][1], diagnostic.ENTITLEMENTS)
            self.assertTrue(all(process.ended for process in processes))
            self.assertEqual(json.loads((root / "report.json").read_text())["conclusion"], report["conclusion"])

    @unittest.skipIf(os.getuid() == 0, "diagnostic intentionally refuses root")
    def test_cleanup_failure_refuses_success_and_attempts_both_targets(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            processes = []
            stopped = []

            def build(directory, source, name, entitlements, environment):
                binary = directory / name
                binary.write_bytes(b"fixture")
                return binary

            def start(args, **kwargs):
                process = SimpleNamespace(pid=12100 + len(processes), stdout=io.BytesIO(), ended=False)
                process.poll = lambda p=process: 0 if p.ended else None
                processes.append(process)
                return process

            def inspect(args, environment, cwd, timeout=30):
                pid = int(args[-2])
                return SimpleNamespace(stdout=json.dumps({"pid": pid, "uid": os.getuid(),
                    "kern_return": 0 if pid == 12101 else 5, "acquired": pid == 12101}))

            def stop(process):
                stopped.append(process.pid)
                if process.pid == 12100:
                    raise OSError("first cleanup failed")
                process.ended = True

            with patch.object(diagnostic.platform, "system", return_value="Darwin"), \
                 patch.object(diagnostic.tempfile, "mkdtemp", return_value=str(root)), \
                 patch.object(diagnostic, "_build", side_effect=build), \
                 patch.object(diagnostic, "sandbox_profile", return_value="exact outer policy"), \
                 patch.object(diagnostic.subprocess, "Popen", side_effect=start), \
                 patch.object(diagnostic, "_ready"), \
                 patch.object(diagnostic, "_command", side_effect=inspect), \
                 patch.object(diagnostic, "stop_probe", side_effect=stop):
                with self.assertRaisesRegex(HarnessError, "cleanup failed"):
                    diagnostic.run()
            self.assertEqual(stopped, [12100, 12101])
            report_file = root / "report.json"
            report = json.loads(report_file.read_text())
            self.assertEqual(report["conclusion"], "EXPERIMENT_FAILED")
            self.assertFalse(report["targets_stopped"])
            self.assertIn("first cleanup failed", report["cleanup_errors"])
            self.assertEqual(report_file.stat().st_mode & 0o777, 0o600)
            self.assertTrue(all(p.stdout.closed for p in processes))

    @unittest.skipIf(os.getuid() == 0, "diagnostic intentionally refuses root")
    def test_stops_target_when_inspector_fails_or_changes_identity(self):
        self.exercise_failure(HarnessError("inspector failed"))
        self.exercise_failure({"pid": 12346, "uid": os.getuid(), "kern_return": 0, "acquired": True})


if __name__ == "__main__":
    unittest.main()
