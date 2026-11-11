import AppKit
import Darwin
import Foundation

private final class LauncherDelegate: NSObject, NSApplicationDelegate, NSWindowDelegate {
    private enum WorkerMode { case start, forget }

    private static let rememberLoginKey = "rememberUntappedLogin"
    private var window: NSWindow!
    private let statusLabel = NSTextField(labelWithString: "Ready to start Slay the Spire 2 and Untapped.")
    private let startButton = NSButton(title: "Start Game", target: nil, action: nil)
    private let signInButton = NSButton(title: "Open Untapped Sign-in", target: nil, action: nil)
    private let stopButton = NSButton(title: "Stop Companion", target: nil, action: nil)
    private let rememberLoginCheckbox = NSButton(checkboxWithTitle: "Remember my Untapped login", target: nil, action: nil)
    private let forgetLoginButton = NSButton(title: "Forget saved login", target: nil, action: nil)
    private var worker: Process?
    private var workerMode: WorkerMode?
    private var input: FileHandle?
    private var output: FileHandle?
    private var pendingOutput = Data()
    private var steamAlert: NSAlert?
    private var stopping = false
    private var quitAfterStop = false
    private var terminalOutcome: LauncherTerminalOutcome?
    private let maximumLineBytes = 64 * 1024

    func applicationDidFinishLaunching(_ notification: Notification) {
        signal(SIGPIPE, SIG_IGN)
        NSApp.setActivationPolicy(.regular)
        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 520, height: 340),
            styleMask: [.titled, .closable, .miniaturizable],
            backing: .buffered,
            defer: false
        )
        window.title = "Slay the Spire 2 + Untapped"
        window.center()
        window.delegate = self
        self.window = window

        let heading = NSTextField(labelWithString: "Slay the Spire 2 + Untapped")
        heading.font = .boldSystemFont(ofSize: 20)
        let detail = NSTextField(wrappingLabelWithString: "Start launches your copied game and companion using your existing Steam progress. Sign in manually the first time; if selected, Keychain stores your Untapped login tokens for automatic restoration on later starts. Stopping the companion leaves the game open; quit it normally.")
        detail.textColor = .secondaryLabelColor
        detail.preferredMaxLayoutWidth = 472
        detail.maximumNumberOfLines = 5
        statusLabel.preferredMaxLayoutWidth = 472
        statusLabel.lineBreakMode = .byWordWrapping
        statusLabel.maximumNumberOfLines = 3
        statusLabel.setContentCompressionResistancePriority(.defaultLow, for: .horizontal)

        startButton.target = self
        startButton.action = #selector(startClicked)
        startButton.bezelStyle = .rounded
        signInButton.target = self
        signInButton.action = #selector(signInClicked)
        signInButton.isEnabled = false
        stopButton.target = self
        stopButton.action = #selector(stopClicked)
        stopButton.isEnabled = false
        rememberLoginCheckbox.target = self
        rememberLoginCheckbox.action = #selector(rememberLoginChanged)
        rememberLoginCheckbox.state = UserDefaults.standard.bool(forKey: Self.rememberLoginKey) ? .on : .off
        forgetLoginButton.target = self
        forgetLoginButton.action = #selector(forgetLoginClicked)

        let buttons = NSStackView(views: [startButton, signInButton, stopButton])
        buttons.orientation = .horizontal
        buttons.spacing = 10
        let loginControls = NSStackView(views: [rememberLoginCheckbox, forgetLoginButton])
        loginControls.orientation = .horizontal
        loginControls.spacing = 12
        let content = NSStackView(views: [heading, detail, loginControls, statusLabel, buttons])
        content.orientation = .vertical
        content.alignment = .leading
        content.spacing = 14
        content.edgeInsets = NSEdgeInsets(top: 24, left: 24, bottom: 24, right: 24)
        content.translatesAutoresizingMaskIntoConstraints = false
        window.contentView?.addSubview(content)
        NSLayoutConstraint.activate([
            content.leadingAnchor.constraint(equalTo: window.contentView!.leadingAnchor),
            content.trailingAnchor.constraint(equalTo: window.contentView!.trailingAnchor),
            content.topAnchor.constraint(equalTo: window.contentView!.topAnchor),
            content.bottomAnchor.constraint(lessThanOrEqualTo: window.contentView!.bottomAnchor)
        ])
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    @objc private func startClicked() {
        guard worker == nil else { return }
        let alert = NSAlert()
        alert.messageText = "Confirm Steam and game are closed"
        alert.informativeText = "Steam Cloud must be up to date. Quit Steam and all game copies before starting. This uses your existing Steam progress."
        alert.alertStyle = .warning
        alert.addButton(withTitle: "Start Game")
        alert.addButton(withTitle: "Cancel")
        alert.beginSheetModal(for: window) { [weak self] response in
            guard response == .alertFirstButtonReturn else { return }
            self?.startWorker(mode: .start)
        }
    }

    @objc private func rememberLoginChanged() {
        UserDefaults.standard.set(rememberLoginCheckbox.state == .on, forKey: Self.rememberLoginKey)
    }

    @objc private func forgetLoginClicked() {
        guard worker == nil else { return }
        startWorker(mode: .forget)
    }

    private func startWorker(mode: WorkerMode) {
        guard worker == nil else { return }
        guard let resourceURL = Bundle.main.resourceURL else {
            showError("App resources are missing.")
            return
        }
        let runtimeURL = resourceURL.appendingPathComponent("runtime", isDirectory: true)
        let configURL = resourceURL.appendingPathComponent("config.json")
        var isDirectory: ObjCBool = false
        guard let configData = try? Data(contentsOf: configURL),
              let config = try? JSONSerialization.jsonObject(with: configData) as? [String: Any],
              let python = config["python"] as? String,
              python.hasPrefix("/"),
              FileManager.default.isExecutableFile(atPath: python),
              FileManager.default.fileExists(atPath: runtimeURL.path, isDirectory: &isDirectory),
              isDirectory.boolValue else {
            showError("The bundled runtime or Python configuration is invalid.")
            return
        }

        let needsKeychainHelper = mode == .forget || rememberLoginCheckbox.state == .on
        var keychainArguments: [String] = []
        if needsKeychainHelper {
            guard let hash = config["keychain_helper_sha256"] as? String,
                  hash.count == 64,
                  hash.utf8.allSatisfy({ (48...57).contains($0) || (65...70).contains($0) || (97...102).contains($0) }),
                  let executableURL = Bundle.main.executableURL else {
                showError("The bundled Keychain helper configuration is invalid.")
                return
            }
            let helperURL = executableURL.deletingLastPathComponent().appendingPathComponent("KeychainHelper")
            guard FileManager.default.isExecutableFile(atPath: helperURL.path) else {
                showError("The bundled Keychain helper is missing or cannot run.")
                return
            }
            keychainArguments = ["--keychain-helper", helperURL.path, "--keychain-sha256", hash]
        }

        let process = Process()
        let stdin = Pipe()
        let stdout = Pipe()
        process.executableURL = URL(fileURLWithPath: python)
        process.arguments = ["-B", "-m", "harness.desktop_launcher", "--gui-worker"] + keychainArguments
        if mode == .forget {
            process.arguments?.append("--forget-login")
        } else if rememberLoginCheckbox.state == .on {
            process.arguments?.append("--remember-login")
        }
        process.currentDirectoryURL = runtimeURL
        process.standardInput = stdin
        process.standardOutput = stdout
        process.standardError = FileHandle.nullDevice
        process.environment = [
            "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
            "LANG": "en_US.UTF-8",
            "HOME": NSHomeDirectory(),
            "TMPDIR": NSTemporaryDirectory()
        ]
        do {
            try process.run()
        } catch {
            showError("Could not start the launcher worker: \(error.localizedDescription)")
            return
        }

        worker = process
        workerMode = mode
        input = stdin.fileHandleForWriting
        output = stdout.fileHandleForReading
        pendingOutput.removeAll(keepingCapacity: true)
        stopping = false
        terminalOutcome = nil
        startButton.isEnabled = false
        forgetLoginButton.isEnabled = false
        rememberLoginCheckbox.isEnabled = false
        signInButton.isEnabled = false
        stopButton.isEnabled = mode == .start
        statusLabel.stringValue = mode == .forget ? "Forgetting saved Untapped login…" : "Checking the game, companion and progress backup…"

        let readHandle = stdout.fileHandleForReading
        DispatchQueue.global(qos: .utility).async { [weak self] in
            drainLauncherWorker(process: process, output: readHandle, onChunk: { data in
                DispatchQueue.main.async { self?.receive(data) }
            }, onReadError: {
                DispatchQueue.main.async {
                    self?.requestStop()
                    self?.terminalOutcome = .error
                    self?.statusLabel.stringValue = mode == .forget
                        ? "Could not read the saved login removal report."
                        : "Could not read the worker session report. Quit any running game normally."
                }
            }, onExit: { terminated in
                DispatchQueue.main.async { self?.workerExited(terminated) }
            })
        }
    }

    private func receive(_ data: Data) {
        guard worker != nil else { return }
        if data.isEmpty {
            output?.readabilityHandler = nil
            return
        }
        pendingOutput.append(data)
        while let newline = pendingOutput.firstIndex(of: 0x0A) {
            guard newline <= maximumLineBytes else { rejectWorkerOutput(); return }
            let line = pendingOutput.prefix(upTo: newline)
            pendingOutput.removeSubrange(...newline)
            handleLine(Data(line))
        }
        if pendingOutput.count > maximumLineBytes { rejectWorkerOutput() }
    }

    private func handleLine(_ data: Data) {
        guard let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let event = object["event"] as? String else {
            rejectWorkerOutput()
            return
        }
        switch event {
        case "status":
            if let message = object["message"] as? String { statusLabel.stringValue = message }
        case "steam_confirmation":
            guard workerMode == .start else { rejectWorkerOutput(); return }
            guard !stopping, steamAlert == nil else { return }
            let alert = NSAlert()
            alert.messageText = "Confirm Steam is ready"
            alert.informativeText = "Open Steam with the intended account, wait for Cloud to finish synchronizing, and confirm the account and progress before continuing."
            alert.alertStyle = .warning
            alert.addButton(withTitle: "Continue")
            alert.addButton(withTitle: "Cancel")
            steamAlert = alert
            alert.beginSheetModal(for: window) { [weak self] response in
                guard let self = self else { return }
                self.steamAlert = nil
                if response == .alertFirstButtonReturn && !self.stopping {
                    self.send("steam_ready")
                } else {
                    self.requestStop()
                }
            }
        case "signin_ready":
            guard workerMode == .start else { rejectWorkerOutput(); return }
            if !stopping {
                signInButton.isEnabled = true
                statusLabel.stringValue = rememberLoginCheckbox.state == .on
                    ? "Untapped is ready. Saved login restores automatically. If asked, click Log in, then Open Untapped Sign-in here."
                    : "Untapped is ready. Click Log in in the companion, then use Open Untapped Sign-in here."
            }
        case "finished":
            terminalOutcome = .finished
            if workerMode == .forget {
                statusLabel.stringValue = "Finishing saved login removal…"
            } else {
                statusLabel.stringValue = (object["message"] as? String) ?? "Companion finished. The game remains open; quit it normally."
            }
            signInButton.isEnabled = false
            stopButton.isEnabled = false
        case "error":
            terminalOutcome = .error
            statusLabel.stringValue = (object["message"] as? String) ?? "The launcher worker reported an error."
            signInButton.isEnabled = false
        default:
            rejectWorkerOutput()
        }
    }

    private func rejectWorkerOutput() {
        statusLabel.stringValue = workerMode == .forget
            ? "The launcher worker sent an invalid saved login event."
            : "The launcher worker sent an invalid event. Stopping the companion."
        requestStop()
    }

    @objc private func signInClicked() {
        guard worker != nil, workerMode == .start, signInButton.isEnabled, !stopping else { return }
        send("sign_in")
    }

    @objc private func stopClicked() { requestStop() }

    private func send(_ action: String) {
        guard let input = input,
              let data = try? JSONSerialization.data(withJSONObject: ["action": action]),
              var line = String(data: data, encoding: .utf8) else { return }
        line += "\n"
        do {
            try input.write(contentsOf: Data(line.utf8))
        } catch {
            statusLabel.stringValue = workerMode == .forget
                ? "The saved login worker connection closed."
                : "The worker connection closed. The game remains open; quit it normally."
            requestStop()
        }
    }

    private func requestStop() {
        guard worker != nil, !stopping else { return }
        stopping = true
        signInButton.isEnabled = false
        stopButton.isEnabled = false
        statusLabel.stringValue = workerMode == .forget
            ? "Stopping saved login removal…"
            : "Stopping the companion. The game remains open; quit it normally."
        if let alert = steamAlert { window.endSheet(alert.window, returnCode: .alertSecondButtonReturn) }
        send("stop")
        try? input?.close()
        input = nil
    }

    private func workerExited(_ process: Process) {
        guard worker === process else { return }
        let mode = workerMode
        let forgetSucceeded = mode == .forget && terminalOutcome == .finished
            && process.terminationStatus == 0 && !stopping
        output?.readabilityHandler = nil
        try? output?.close()
        try? input?.close()
        output = nil
        input = nil
        worker = nil
        workerMode = nil
        pendingOutput.removeAll()
        steamAlert = nil
        startButton.isEnabled = true
        forgetLoginButton.isEnabled = true
        rememberLoginCheckbox.isEnabled = true
        signInButton.isEnabled = false
        stopButton.isEnabled = false
        if mode == .forget {
            if forgetSucceeded {
                rememberLoginCheckbox.state = .off
                UserDefaults.standard.set(false, forKey: Self.rememberLoginKey)
                statusLabel.stringValue = "Saved Untapped login forgotten."
            } else if terminalOutcome != .error {
                statusLabel.stringValue = process.terminationStatus == 0
                    ? "Saved login removal did not finish."
                    : "Saved login removal failed with status \(process.terminationStatus)."
            }
        } else {
            statusLabel.stringValue = launcherFinalMessage(current: statusLabel.stringValue,
                outcome: terminalOutcome, exitStatus: process.terminationStatus, stopping: stopping)
        }
        stopping = false
        if launcherShouldQuit(requested: quitAfterStop, outcome: terminalOutcome, exitStatus: process.terminationStatus) {
            NSApp.terminate(nil)
        } else if quitAfterStop {
            quitAfterStop = false
            showError(statusLabel.stringValue)
        }
    }

    private func showError(_ message: String) {
        statusLabel.stringValue = message
        let alert = NSAlert()
        alert.messageText = "Launcher error"
        alert.informativeText = message
        alert.alertStyle = .critical
        alert.beginSheetModal(for: window)
    }

    func windowShouldClose(_ sender: NSWindow) -> Bool {
        guard worker != nil else { return true }
        let alert = NSAlert()
        if workerMode == .forget {
            alert.messageText = "Stop saved login removal and close launcher?"
            alert.informativeText = "The saved login may remain in Keychain."
            alert.addButton(withTitle: "Stop and Quit")
        } else {
            alert.messageText = "Stop companion and close launcher?"
            alert.informativeText = "The companion will stop. Slay the Spire 2 remains open; quit it normally."
            alert.addButton(withTitle: "Stop Companion and Quit")
        }
        alert.addButton(withTitle: "Keep Launcher Open")
        alert.beginSheetModal(for: window) { [weak self] response in
            guard response == .alertFirstButtonReturn else { return }
            self?.quitAfterStop = true
            self?.requestStop()
        }
        return false
    }

    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        guard worker != nil else { return .terminateNow }
        _ = windowShouldClose(window)
        return .terminateCancel
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        true
    }
}

@main
private enum LauncherApplication {
    static func main() {
        let application = NSApplication.shared
        let delegate = LauncherDelegate()
        application.delegate = delegate
        application.run()
    }
}
