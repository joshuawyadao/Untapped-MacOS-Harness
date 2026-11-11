# Desktop launcher

The dedicated **Slay the Spire 2 + Untapped** app runs the prepared game copy with existing Steam progress and the verified companion, without Terminal commands. It is an experimental launcher, not a certification of unattended reliability.

## Use

1. Finish any current game normally, allow Steam Cloud to finish syncing, then quit Steam and all game copies.
2. Open **Slay the Spire 2 + Untapped** in your user's Applications folder. Click **Start Game** and confirm that Cloud is current and Steam/game are closed.
3. The launcher verifies its prepared apps and backs up progress, then opens Steam. In the native dialog, confirm the intended Steam account and completed synchronization; click **Continue**. Changed progress/source checks can refuse startup and require a fresh attempt.
4. The game and companion start. In Untapped, click **Log in**. Then click **Open Untapped Sign-in** in the launcher and complete the browser flow yourself. The button can be retried if the URL is not ready yet. Terms and credentials remain owner-controlled.
5. Quit the game normally when finished and let Steam Cloud sync. **Stop Companion** or closing the launcher requests companion cleanup and leaves any running game open.

To keep the launcher in the Dock, right-click its running Dock icon and choose **Options → Keep in Dock**. Pinning is a one-time action. Launching the ordinary Steam game directly does not automatically attach this harness.

## Session behavior

The desktop worker uses game-lifetime mode: no four-hour or eight-hour session cutoff. Required game-identity monitoring, account mismatch detection, companion exit/failure handling and gateway cleanup remain active. Startup/network operation timeouts still apply. Owner stop is a normal outcome when cleanup succeeds, including before authentication. Existing CLI launches retain their finite defaults; `--until-game-exit` explicitly selects the new mode and is mutually exclusive with `--minutes`.

A filesystem lock prevents two desktop workers from running concurrently. LaunchServices also normally reuses the existing app. CLI conflicts are still checked through the existing game/Steam inventory. GUI cancellation is checked before game creation and during supervision; the game is never terminated by companion cleanup.

## Build and installation

From the refinement checkout, on the prepared macOS account:

```sh
python3 -m harness.desktop_install --destination "$HOME/Applications/Slay the Spire 2 + Untapped.app"
```

The destination must not already exist. Preserve a previous launcher when rebuilding and install to a new destination. The builder compiles AppKit source with the local Swift toolchain, includes a snapshot of the Python/C/JavaScript harness sources, copies the owner's local game icon, and ad-hoc signs/verifies the new app. It does not launch a game. Existing game/companion signatures and settings are not modified. The launcher uses the selected installed UI version, including the attack-icon repair. It depends on the local Python executable recorded at build time; rebuilding is necessary if that interpreter is removed or when updating the bundled harness snapshot.

The native frontend communicates with the worker over bounded JSON lines. UI output contains fixed status text only; vendor output goes to private workspace run logs. The sign-in action reads an owned mode-0600 regular file with no symlink or hard-link indirection, validates the fixed accounts.untapped.gg OAuth contract and localhost callback, then opens it only on the owner's button action. URLs/account credentials are not included in UI events. No login item, background launch agent, credential persistence or Steam Play interception is installed.

## Validation and limitations

The November 10, 2026 build compiled and passed native signature verification. The installed app window was inspected with Start Game enabled and sign-in/stop disabled while idle. All 272 regression tests passed, including new lifetime, cancellation, private URL, exclusive-lock and worker-protocol cases. Native Dock automation timed out, so pinning is left to the owner.

The first complete real-game launch through the new app, browser login through its button, multi-hour sessions and quit behavior remain live checks. The earlier diagnostic session ended with a supervision failure whose underlying cause was not established; removing the duration limit does not resolve or conceal that separate issue. Private diagnostics and existing failure outcomes remain available.
