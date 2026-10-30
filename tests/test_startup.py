"""Startup milestone classification from synthetic local probe files."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from harness import cli


class StartupStatusTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.session = Path(self.temporary.name).resolve()
        (self.session / "profile").mkdir()
        (self.session / "manifest.json").write_text("{}")
        (self.session / "profile/events.jsonl").write_text(
            json.dumps({"event": "bootstrap"}) + "\n" + json.dumps({"event": "ready"}) + "\n"
        )

    def test_electron_ready_without_vendor_core_is_not_companion_initialization(self):
        result = cli.status(self.session)
        self.assertEqual(result["startup"], "ELECTRON_READY")
        self.assertEqual(result["companion_initialization"], "NOT_OBSERVED")
        self.assertEqual(result["startup_blockers"], [])
        self.assertEqual(result["attachment"], "UNTESTED")
        self.assertEqual(result["state_reading"], "UNTESTED")

    def test_socket_and_child_sandbox_failures_are_separate_blockers(self):
        (self.session / "stdout.log").write_text(
            "Failed to create socket directory: Operation not permitted\n"
            "[123] sandbox initialization failed: Operation not permitted\n"
        )
        result = cli.status(self.session)
        self.assertEqual(result["startup"], "ELECTRON_READY")
        self.assertEqual(set(result["startup_blockers"]), {
            "singleton_socket_directory", "child_sandbox_initialization",
        })
        self.assertEqual(result["companion_initialization"], "NOT_OBSERVED")

    def test_vendor_terms_and_core_logs_are_classified_without_accepting_terms(self):
        log = self.session / "profile/log.log"
        log.write_text("[Core] Showing Terms of Service\n")
        terms = cli.status(self.session)
        self.assertEqual(terms["companion_initialization"], "TERMS_LOGGED")
        self.assertTrue(terms["terms_screen_logged"])
        log.write_text("[Core] Showing Terms of Service\n[Core] Fully initialized\n")
        initialized = cli.status(self.session)
        self.assertEqual(initialized["companion_initialization"], "CORE_INITIALIZED_LOGGED")

    def test_status_does_not_infer_core_from_ambiguous_instance_warning(self):
        (self.session / "stdout.log").write_text("Another instance of the app is already running\n")
        result = cli.status(self.session)
        self.assertEqual(result["companion_initialization"], "NOT_OBSERVED")
        self.assertEqual(result["startup_blockers"], [])

    def test_launch_cli_returns_nonzero_when_blocker_exists_despite_electron_ready(self):
        fake = {
            "startup": "ELECTRON_READY", "companion_initialization": "NOT_OBSERVED",
            "startup_blockers": ["singleton_socket_directory"],
        }
        output = io.StringIO()
        with mock.patch.object(cli, "launch", return_value=fake), contextlib.redirect_stdout(output):
            exit_code = cli.main(["launch", str(self.session), "--seconds", "15"])
        self.assertEqual(exit_code, 1)
        self.assertIn("singleton_socket_directory", output.getvalue())

    def test_launch_environment_and_probe_create_short_chromium_temp(self):
        expected = str(self.session / "t")
        self.assertEqual(cli.launch_environment(self.session)["MAC_CHROMIUM_TMPDIR"], expected)
        app = self.session / "Companion.app/Contents"
        for relative in (
            "Resources/app.asar", "MacOS/Untapped.gg Companion",
            "Frameworks/Electron Framework.framework/Versions/A/Electron Framework",
            "Resources/app.asar.unpacked/" + cli.SCRY,
        ):
            target = app / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"synthetic")
        (self.session / "manifest.json").write_text(json.dumps({"patched_asar_sha256": "synthetic-pin"}))
        process = mock.Mock(pid=54321)
        process.wait.return_value = 0

        def start_process(*_args, **kwargs):
            self.assertTrue((self.session / "t").is_dir())
            self.assertEqual(kwargs["env"]["MAC_CHROMIUM_TMPDIR"], expected)
            return process

        with mock.patch.object(cli.platform, "system", return_value="Darwin"), \
                mock.patch.object(cli, "sha256", return_value="synthetic-pin"), \
                mock.patch.object(cli, "expected_executable_hash", return_value="synthetic-pin"), \
                mock.patch.object(cli, "FRAMEWORK_SHA256", "synthetic-pin"), \
                mock.patch.object(cli, "SCRY_SHA256", "synthetic-pin"), \
                mock.patch.object(cli.subprocess, "Popen", side_effect=start_process), \
                mock.patch.object(cli, "stop_probe"), \
                mock.patch.object(cli, "status", return_value={"startup": "NOT_OBSERVED"}):
            cli.launch(self.session, 1)


if __name__ == "__main__":
    unittest.main()
