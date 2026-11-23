# Desktop launcher

The dedicated **Slay the Spire 2 + Untapped** app runs the prepared game copy with existing Steam progress and the verified companion, without Terminal commands. It is an experimental launcher, not a certification of unattended reliability.

## Use

1. Finish any current game normally, allow Steam Cloud to finish syncing, then quit Steam and all game copies.
2. Open **Slay the Spire 2 + Untapped** in your user's Applications folder. Click **Start Game** and confirm that Cloud is current and Steam/game are closed.
3. The launcher verifies its prepared apps and backs up progress, then opens Steam. In the native dialog, confirm the intended Steam account and completed synchronization; click **Continue**. Changed progress/source checks can refuse startup and require a fresh attempt.
4. To save your Untapped login, select **Remember my Untapped login** before starting (off by default). On the first start, click **Log in** in Untapped, then **Open Untapped Sign-in** in the launcher and complete the browser flow yourself. The button can be retried if the URL is not ready yet. Later starts with Remember enabled restore the saved login automatically; denied, expired or revoked credentials fall back to manual sign-in. Terms remain owner-controlled.
5. Quit the game normally when finished and let Steam Cloud sync. **Stop Companion** or closing the launcher requests companion cleanup and leaves any running game open.

While the launcher is idle, **Forget saved login** deletes its dedicated Keychain item and switches Remember off after successful deletion. Forget remains available if a game update invalidates launch preparation. Unchecking Remember skips Keychain access on future starts but does not delete a saved item. Steam account and Cloud confirmations still apply.

To keep the launcher in the Dock, right-click its running Dock icon and choose **Options → Keep in Dock**. Pinning is a one-time action. Launching the ordinary Steam game directly does not automatically attach this harness.

## Session behavior

The desktop worker uses game-lifetime mode: no four-hour or eight-hour session cutoff. Required game-identity monitoring, account mismatch detection, companion exit/failure handling and gateway cleanup remain active. Startup/network operation timeouts still apply. Owner stop is a normal outcome when cleanup succeeds, including before authentication. Existing CLI launches retain their finite defaults; `--until-game-exit` explicitly selects the new mode and is mutually exclusive with `--minutes`.

A filesystem lock prevents two desktop workers from running concurrently. LaunchServices also normally reuses the existing app. CLI conflicts are still checked through the existing game/Steam inventory. GUI cancellation is checked before game creation and during supervision; the game is never terminated by companion cleanup.

If the supervised game exits with a signal or nonzero status during play, the launcher displays “Slay the Spire 2 crashed.” It also displays this message when the exit status arrives during companion cleanup. The private run summary records the game's exit code.

## Build and installation

If Steam updates the game, the launcher may stop with “The installed game changed.” The [reviewed game-version update](Game-Version-Updates.md) adds a separately pinned v0.111.1 copy while retaining the original activation and Steam progress; rebuild the launcher after that update is verified. A rebuild alone cannot approve an unknown source build.

The combined launcher was installed at the usual Applications path on November 18, 2026. It uses the native inventory worker during play and reports confirmed game crashes. The prior signed launcher is retained for rollback. [Combined launcher verification](Verification.md#combined-everyday-launcher)

November 17 live verification confirmed starting-choice and reward tier badges plus a matched combat Attacks panel on v0.111.1 with the existing Steam/profile binding. The original copied game and verified pre-update progress backup are retained. Continue to use the normal Steam Cloud startup and quit workflow.

From the refinement checkout, on the prepared macOS account:

```sh
python3 -m harness.desktop_install --destination "$HOME/Applications/Slay the Spire 2 + Untapped.app"
```

The destination must not already exist. Preserve a previous launcher when rebuilding and install to a new destination. The builder compiles AppKit and Security.framework helper sources with the local Swift toolchain, includes a snapshot of the Python/C/JavaScript harness sources, copies the owner's local game icon, and ad-hoc signs/verifies the new app. It does not launch a game. The build itself does not modify existing game/companion signatures or settings. To enable remembered login on an existing prepared installation, first run `python3 -m harness.login_update --install-main`; it creates and verifies a separately signed companion copy and selection receipt, retaining the earlier UI copy. The launcher uses the selected installed UI version, including the attack-icon repair. It depends on the local Python executable recorded at build time; rebuilding is necessary if that interpreter is removed or when updating the bundled harness snapshot.

The native frontend communicates with the worker over bounded JSON lines. UI output contains fixed status text only; vendor output goes to private workspace run logs. The sign-in action reads an owned mode-0600 regular file with no symlink or hard-link indirection, validates the fixed accounts.untapped.gg OAuth contract and localhost callback, then opens it only on the owner's button action. URLs/account credentials are not included in UI events. No login item, background launch agent or Steam Play interception is installed. Optional credential persistence uses only the harness-specific Keychain item described below.

## Validation and limitations

The November 10, 2026 build compiled and passed native signature verification. The installed app window was inspected with Start Game enabled and sign-in/stop disabled while idle. All 272 regression tests passed, including new lifetime, cancellation, private URL, exclusive-lock and worker-protocol cases. Native Dock automation timed out, so pinning is left to the owner.

The first complete real-game launch through the new app, browser login through its button, multi-hour sessions and quit behavior remain live checks. The earlier diagnostic session ended with a supervision failure whose underlying cause was not established; removing the duration limit does not resolve or conceal that separate issue. Private diagnostics and existing failure outcomes remain available.

### Short live status messages

The November 11 live-startup fix uses POSIX pipe reads so short prompts arrive while the worker waits for owner input, rather than only when the worker exits. Both interactive status delivery and final-message ordering have native regressions. If a startup is cancelled after Steam opens, leave any game quit normally, let Cloud synchronize, then quit Steam before retrying.

### Remembered login

The dedicated generic-password item uses service `local.untapped.sts2.harness.login` and account `remembered-session-v1`, accessible when the user Keychain is unlocked. It stores one account email and its global OAuth access/refresh tokens, never the account password or Steam credentials. The checkbox preference is a Boolean in UserDefaults. Signing into a different account replaces the saved account; token refresh updates the item, and vendor logout or an invalid global token clears it.

The companion retains its outer sandbox, blocked direct Keychain access and fixed gateway routes. A per-session capability protects a mode-0600 Unix socket inside its private attempt. The signed host helper is SHA-256 pinned; credential data crosses bounded stdin/stdout and socket messages rather than command arguments, environment variables or credential files. Existing vendor logs remain private and must not be shared. Broker shutdown drains active writes before releasing the desktop lock, preventing a delayed write after Forget. A Keychain denial or timeout leaves session login in memory and emits a fixed warning.

Automated tests use synthetic credentials and fake Keychain operations. Native compilation/signature and idle controls can be verified without touching Keychain. Initial real sign-in, Keychain consent and a later automatic restore are owner-run validation steps; a system Keychain prompt may require approval. No automatic browser login or password entry is performed.

The November 11 remembered-login build is installed at the original user Applications path, with the preceding app retained for rollback. Its deep signature, signed helper hash and all 36 bundled runtime sources verified. The opened idle window displays Remember unchecked and Forget/Start enabled. The owner must enable Remember and sign in once, then verify automatic restoration on a later start; no real credentials were read or stored during installation.


### Service-name correction

The first remembered-login build used the wrong vendor keytar service name, so successful sign-in stayed in memory and did not reach Keychain. The corrected bridge matches Untapped's service under the launcher sandbox ID. The updater publishes `companion-login-v2.json` with the corrected helper hash and preserves the v1 copy/receipt; rerun the same `harness.login_update --install-main` command before rebuilding an older installation. Invalid or incomplete metadata is rejected.

After the corrected launcher is installed, keep Remember enabled and sign in once more. The earlier session cannot supply a saved login because its save calls bypassed the bridge. Check the dedicated item's presence without printing credentials, then quit normally and start again to verify automatic restoration. Do not log out of Untapped between those starts: logout intentionally deletes the saved login. Steam/Cloud confirmations still apply.

The corrected service-name build is installed at the original Applications path, with the previous launcher retained for rollback. Native signatures and all 36 runtime files verified, and the reopened idle window retains the owner's Remember preference. A fresh sign-in and saved-item check must precede the real automatic-sign-in test.


### Supervision failure diagnostics

When an unhandled supervision check throws, the launcher names the check and a fixed error category, for example “Supervision stopped during game process inventory (timeout).” Confirmed identity mismatches remain fatal; the bounded timeout policy below handles only process-inventory timeouts. Finish any running game normally; use this launcher for the next start rather than macOS Reopen on the copied companion.

The sanitized `sts2main-controlled.*.json` report records `supervision_diagnostics` (schema, bounded check counter, last started/completed checks, last-check duration and first failure), `failure_before_cleanup`, `cleanup_failures`, and companion exit codes before/after cleanup. `companion_termination_requested` says whether the main process was still observed alive when cleanup was requested; an exit after that request does not by itself establish the initiating cause. Cleanup uses the already reaped process result without an extra polling operation. The old top-level reason/stage/exit fields remain available.

Reports contain only fixed check/category names and bounded numeric errno/return-code evidence. They exclude exception messages, class names, tracebacks, command arguments, paths, account details, tokens and raw vendor logs. No diagnostic history is accumulated in memory. For another failure, keep the launcher error visible and ask for the newest sanitized report; the original private attempt and OS crash evidence remain separate. These diagnostics describe future failures and cannot recover the exception discarded by the preceding build.

The November 16 diagnostic build is installed at the original Applications path with a rollback bundle retained. Native signatures, the helper pin and all 37 runtime files verified. The opened idle launcher retains Remember enabled. Start normally for the next test; if Untapped closes, keep the launcher error visible and report the triggering activity so the new check/category and cleanup records can be inspected.


### Live process inventory and timeout recovery

During play, the launcher reuses one unprivileged macOS worker and requests a fresh process snapshot on each guard pass. The guard still checks ownership, the verified game path and PID, the process group, and conflicting Steam or game processes. Pre-launch checks use the system process inventory as before. A foreign executable path that cannot be resolved while its process is still present triggers a legacy scan within the same attempt. See the [architecture notes](Harness-Architecture.md#bounded-live-inventory-retries) for the process metadata used and the [benchmark](Verification.md#live-process-inventory-cpu-benchmark) for measured CPU use.

Each live inventory attempt has a two-second deadline. When the native worker times out, the launcher discards that request and tries a fresh system `ps` scan on the next attempt. It can retry while the timed-out worker is still being reaped. Six consecutive `GAME_PROCESS_INVENTORY` timeouts stop the companion and retain a fatal diagnostic. The first two retry delays are 250 ms and the next three are one second. A fresh, verified check resets the consecutive budget.

During retry backoff the supervisor checks account mismatch, game exit/crash, companion exit, owner cancellation and any finite session deadline, polling the delay at most 50 ms at a time. A confirmed mismatch stops immediately when detected. Non-timeout inventory errors and timeouts from other checks follow their existing stop paths. Process creation and operating system scheduling can add to the nominal 15.5 seconds across six attempts and five retry delays.

The safe `supervision_diagnostics.inventory_retry` counters record `timeouts`, `retries_scheduled`, `recoveries` and `exhaustions`, plus the latest known fixed timeout phase. The phase distinguishes native or legacy startup, response and reaping. After recovery, the report retains the timeout count and phase. Exhaustion or a later failure retains its own check and category. The report vocabulary excludes process identities and private exception data.

The signed recovery launcher was installed at the usual Applications path on November 23, 2026, with the previous launcher retained for rollback. See the [incident and recovery checks](Verification.md#live-inventory-timeout-recovery) for the failure reproduced by this change.

## Native macOS full-screen overlay

The STS2 overlay uses Electron's macOS `panel` window type so it can float above a native full-screen game. The existing all-workspace/full-screen visibility, click-through behavior, account/profile gate, normal show/hide rules and window sizing remain in place. The option applies only to the STS2 overlay on Darwin; settings and other platform/game windows retain their previous construction.

For a prepared installation, run `python3 -m harness.fullscreen_update --install-main` before rebuilding the native launcher. This publishes a separately verified `companion-fullscreen-v1` copy and receipt above the retained UI/login copies, with the same signing entitlements, native binaries, helper pin and controlled network policy. Fresh companion preparations include the same patch. The launcher validates and selects the complete final layer, including a second selection check before game launch; incomplete or inconsistent metadata stops launch.

Rebuild to a new destination using the existing build command, then replace the installed launcher after normal game closure and Steam Cloud synchronization. Preserve the prior launcher bundle for rollback: its older runtime continues to select the retained login/UI copy. A running session continues using its existing companion until normal exit. Remembered login and Steam progress retain their existing behavior.

Live verification should cover the Untapped U tab while entering/leaving native full screen, followed by tier badges or the Attacks panel on the relevant game screen. A renderer reporting itself visible does not establish that macOS is displaying its window above the game. Windowed visibility was confirmed during diagnosis; the repaired native full-screen behavior requires an owner-visible check after installation.

The November 16 full-screen update is installed at the original Applications path. Its native signatures, signed helper pin and all 39 runtime files verify; the previous launcher is preserved for rollback. The idle window retains Remember enabled. The owner has confirmed overlay visibility with the repaired companion while the game remains in native full screen. The initial sighting was delayed; repeated transitions and other display arrangements remain ongoing use/testing checks.

### Portable and native CI enforcement

Every pull request to main runs the portable harness suite on Ubuntu and a separate macOS job. The macOS job compiles the actual launcher, outcome and Keychain helper sources into runner temporary storage, ad-hoc signs and verifies those inert binaries, and runs the native outcome/streaming seam tests with synthetic system processes. It does not open the launcher, access Keychain, install apps or start a game.

The existing required `CI Verify` check runs after both platform jobs, including when a dependency fails or is skipped. It accepts only explicit success from both jobs; failed, cancelled, skipped, missing, empty or unknown results fail the gate. Branch protection keeps the same required check name. Focused regressions exercise the result script and verify that the aggregate's dependency/condition/result bindings remain on that job, with native compilation and seam tests on `macos-15`.
