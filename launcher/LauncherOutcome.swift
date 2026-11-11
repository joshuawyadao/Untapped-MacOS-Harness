import Foundation

// Owner intent does not certify cleanup. A terminal worker report always wins;
// without one, an abnormal process exit must remain visible as a failure.
enum LauncherTerminalOutcome: String {
    case finished
    case error
}

func launcherFinalMessage(current: String, outcome: LauncherTerminalOutcome?, exitStatus: Int32, stopping: Bool) -> String {
    if outcome != nil { return current }
    if exitStatus != 0 {
        return "Launcher worker exited with status \(exitStatus). Quit any running game normally."
    }
    if stopping { return "Companion stopped. Quit any running game normally."
    }
    return "Launcher worker finished without a session report. Quit any running game normally."
}

func launcherShouldQuit(requested: Bool, outcome: LauncherTerminalOutcome?, exitStatus: Int32) -> Bool {
    return requested && outcome == .finished && exitStatus == 0
}

// Run on one background producer. Chunks, read failures and finalization are
// delivered in this order; callers enqueue all callbacks onto the same UI queue.
func drainLauncherWorker(process: Process, output: FileHandle,
                         onChunk: (Data) -> Void, onReadError: () -> Void,
                         onExit: (Process) -> Void) {
    do {
        while let chunk = try output.read(upToCount: 4096), !chunk.isEmpty {
            onChunk(chunk)
        }
    } catch {
        onReadError()
    }
    process.waitUntilExit()
    onExit(process)
}
