"""Exercise the actual Swift finalization seam; no AppKit or game launch."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


@unittest.skipUnless(sys.platform == 'darwin' and shutil.which('swiftc'), 'Requires the local macOS Swift toolchain')
class NativeOutcomeTests(unittest.TestCase):
    def test_owner_stop_preserves_terminal_cleanup_errors_and_abnormal_exit(self):
        source = Path(__file__).resolve().parents[1] / 'launcher/LauncherOutcome.swift'
        checks = '''
        import Foundation
        let failure = "Gateway cleanup failed"
        for stopping in [false, true] {
            precondition(launcherFinalMessage(current: failure, outcome: .error, exitStatus: 1, stopping: stopping) == failure)
            precondition(launcherFinalMessage(current: "Finished safely", outcome: .finished, exitStatus: 0, stopping: stopping) == "Finished safely")
        }
        precondition(launcherFinalMessage(current: "Stopping", outcome: nil, exitStatus: 1, stopping: true).contains("status 1"))
        precondition(launcherFinalMessage(current: "Stopping", outcome: nil, exitStatus: 0, stopping: true).contains("Companion stopped"))
        precondition(launcherFinalMessage(current: "Running", outcome: nil, exitStatus: 0, stopping: false).contains("without a session report"))
        precondition(!launcherShouldQuit(requested: true, outcome: .error, exitStatus: 1))
        precondition(!launcherShouldQuit(requested: true, outcome: nil, exitStatus: 0))
        precondition(!launcherShouldQuit(requested: true, outcome: .finished, exitStatus: 1))
        precondition(launcherShouldQuit(requested: true, outcome: .finished, exitStatus: 0))
        precondition(!launcherShouldQuit(requested: false, outcome: .finished, exitStatus: 0))
        // Delay every UI callback until the worker has already exited. The
        // reader must still enqueue all status bytes before exit finalization.
        for _ in 0..<20 {
            let process = Process()
            let pipe = Pipe()
            process.executableURL = URL(fileURLWithPath: "/usr/bin/printf")
            process.arguments = ["terminal-session-report"]
            process.standardOutput = pipe
            try process.run()
            var pending: [() -> Void] = []
            var received = Data()
            var finalized = false
            drainLauncherWorker(process: process, output: pipe.fileHandleForReading,
                onChunk: { data in pending.append { precondition(!finalized); received.append(data) } },
                onReadError: { preconditionFailure("Unexpected pipe read failure") },
                onExit: { result in pending.append {
                    precondition(String(data: received, encoding: .utf8) == "terminal-session-report")
                    precondition(result.terminationStatus == 0)
                    finalized = true
                } })
            precondition(!process.isRunning)
            for callback in pending { callback() }
            precondition(finalized)
            try pipe.fileHandleForReading.close()
        }
        print("Native outcome regressions passed")
        '''
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            script=root/'main.swift';script.write_text(checks)
            exe=root/'outcome-tests'
            subprocess.run(['/usr/bin/swiftc','-swift-version','5','-module-cache-path',str(root/'modules'),str(source),str(script),'-o',str(exe)],check=True,capture_output=True)
            result=subprocess.run([str(exe)],check=True,capture_output=True,text=True)
            self.assertIn('Native outcome regressions passed',result.stdout)
