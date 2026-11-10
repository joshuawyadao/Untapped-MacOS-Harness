"""Regressions for truthful attachment evidence and bounded probe processes."""
import json
import os
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from harness import cli, patches


class ProbeTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "posix", "Process groups require POSIX")
    def test_stop_probe_kills_descendant_after_leader_exits(self):
        with tempfile.TemporaryDirectory() as temporary:
            ready = Path(temporary) / "ready"
            child = (
                "import os,signal,time; from pathlib import Path; "
                "signal.signal(signal.SIGTERM,signal.SIG_IGN); "
                f"Path({str(ready)!r}).write_text(str(os.getpid())); time.sleep(60)"
            )
            parent = (
                "import subprocess,sys,time; "
                f"subprocess.Popen([sys.executable,'-c',{child!r}]); time.sleep(60)"
            )
            process = subprocess.Popen([sys.executable, "-c", parent], start_new_session=True,
                                       stdout=subprocess.PIPE)
            try:
                deadline = time.monotonic() + 5
                while not ready.exists() and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertTrue(ready.exists(), "synthetic descendant failed to start")
                cli.stop_probe(process)
                self.assertIsNotNone(process.poll())
                # Both processes hold stdout. EOF proves the descendant also exited.
                readable, _, _ = select.select([process.stdout], [], [], 3)
                self.assertTrue(readable, "descendant still holds the probe pipe open")
                self.assertEqual(process.stdout.read(), b"")
            finally:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
                process.stdout.close()

    def test_launch_failure_is_a_nonzero_cli_result(self):
        with mock.patch.object(cli, "launch", return_value={"startup": "NOT_OBSERVED"}), \
                mock.patch("builtins.print"):
            self.assertEqual(cli.main(["launch", "/synthetic"]), 1)

    @unittest.skipUnless(shutil.which("node"), "Node is required for injected JavaScript checks")
    def test_failed_reader_connection_never_reports_success(self):
        replacement = next(new for old, new in patches.CORE_PATCHES
                           if 'await scry.connect();' in old)
        script = '''
          const assert = require('node:assert/strict');
          const snippet = JSON.parse(process.argv[1]);
          const run = new Function('scry', 'return (async () => {' + snippet + '})()');
          (async () => {
            for (const outcome of [false, true, 'throw']) {
              const events = [];
              global.__untappedHarnessEvent = (name) => events.push(name);
              const scry = { connect: async () => {
                if (outcome === 'throw') throw Error('failed attach');
                return outcome;
              }, startWatcher: () => {} };
              try { await run(scry); } catch (error) { assert.equal(outcome, 'throw'); }
              assert.equal(events.includes('attach-attempt'), true);
              assert.equal(events.includes('reader-connected'), outcome === true);
            }
          })().catch(error => { console.error(error); process.exitCode = 1; });
        '''
        result = subprocess.run([shutil.which("node"), "-e", script, json.dumps(replacement)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
