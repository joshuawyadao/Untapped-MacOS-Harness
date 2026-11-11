# Desktop launcher

The dedicated **Slay the Spire 2 + Untapped** app runs the prepared game copy with existing Steam progress and the verified companion, without Terminal commands. It is an experimental launcher, not a certification of unattended reliability.

## Use

1. Finish any current game normally, allow Steam Cloud to finish syncing, then quit Steam and all game copies.
2. Open **Slay the Spire 2 + Untapped** in your user's Applications folder. Click **Start Game** and confirm that Cloud is current and Steam/game are closed.
3. The launcher verifies its prepared apps and backs up progress, then opens Steam. In the native dialog, confirm the intended Steam account and completed synchronization; click **Continue**. Changed progress/source checks can refuse startup and require a fresh attempt.
4. To save your Untapped login, select **Remember my Untapped login** before starting (off by default). On the first start, click **Log in** in Untapped, then **Open Untapped Sign-in** in the launcher and complete the browser flow yourself. The button can be retried if the URL is not ready yet. Later starts with Remember enabled restore the saved login automatically; denied, expired or revoked credentials fall back to manual sign-in. Terms remain owner-controlled.
5. Quit the game normally when finished and let Steam Cloud sync. **Stop Companion** or closing the launcher requests companion cleanup and leaves any running game open.

While the launcher is idle, **Forget saved login** deletes its dedicated Keychain item and switches Remember off after successful deletion. Unchecking Remember skips Keychain access on future starts but does not delete a saved item. Steam account and Cloud confirmations still apply.

To keep the launcher in the Dock, right-click its running Dock icon and choose **Options → Keep in Dock**. Pinning is a one-time action. Launching the ordinary Steam game directly does not automatically attach this harness.

## Session behavior

The desktop worker uses game-lifetime mode: no four-hour or eight-hour session cutoff. Required game-identity monitoring, account mismatch detection, companion exit/failure handling and gateway cleanup remain active. Startup/network operation timeouts still apply. Owner stop is a normal outcome when cleanup succeeds, including before authentication. Existing CLI launches retain their finite defaults; `--until-game-exit` explicitly selects the new mode and is mutually exclusive with `--minutes`.

A filesystem lock prevents two desktop workers from running concurrently. LaunchServices also normally reuses the existing app. CLI conflicts are still checked through the existing game/Steam inventory. GUI cancellation is checked before game creation and during supervision; the game is never terminated by companion cleanup.

## Build and installation

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
