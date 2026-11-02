# Test account and first boot

The owner approved isolated setup and the confined 60-second first game probe. The game has not yet been launched. The game-only transfer archive contains no saves, Steam settings, credentials, or companion profile.

1. In the MacBook's **Apple menu → System Settings → Users & Groups → Add User**, create a **Standard** account named `sts2test`. Choose the password privately. Stay in the normal account until preparation checks finish.
2. Quit normal STS2 and Steam yourself. When instructed, log out or switch into `sts2test`. Skip Apple Account sign-in and do not open/sign into Steam. Both test apps must ultimately run in this account's graphical session.
3. Open **Terminal** in `sts2test` and run the staged script:

   ```sh
   /bin/sh /private/tmp/untapped-sts2-transfer-01/run_isolated_game_probe.sh
   ```

   The script refuses other account names and existing test directories. It checks the game transfer hash, copies original harness code, extracts a source game copy, verifies the pinned game/signature, prepares a separate unchanged game copy, and launches it with `--force-steam=off --nomods` for at most 60 seconds. No administrator command or game signing is involved. Allow several minutes for extraction, hashing and signature checks before the game window opens.
4. During this first boot, remain at the initial menu. Stop if Steam, a sign-in, migration, imported progress, or an OS permission prompt appears. Do not approve prompts or start a run. The launcher stops its own game process group at the limit and stops if it detects an unexpected Steam/game process.
5. Keep the Terminal output and report the result here after returning to the original account. Logs stay under `~/UntappedSTS2GameSession/game-attempt-*` in the test account. We must verify fresh data paths, Steam-not-initialized state, and cleanup before gameplay; `isolation_verified` deliberately stays false in the launch report.

Writes are confined to the test account home/session. The game launch environment is constructed without inherited Steam overrides or credentials. It does not assign HOME; Godot may use the private working directory as its data root when HOME is absent, while other native APIs may use the actual test account home. The first-boot log must establish the actual path. The policy denies the normal home and remote networking; finite dummy-file/socket probes passed, not a complete security audit.

The companion target guard is now packaged and signed in copy06 for the approved observation. It rejects an absent or mismatched PID, user, or executable immediately before STS2 reader construction. `launch-outer --target-pid PID --target-game '/absolute/copied/game/executable'` supplies the expected identity and performs preflight verification. Copy06 signing is complete; game signing remains outside approval.

## Window visibility retry

The first exported log confirms Steam skipped, a relative private data root `./SlayTheSpire2`, and both essential/complete main-menu load milestones. The owner saw no menu. The shader-cache warning did not prevent these milestones; it does not by itself establish a fatal renderer failure. UI visibility remains unverified.

The updated launcher requests a 1280x720 window at 80,80 with always-on-top using [Godot's display options](https://docs.godotengine.org/en/4.5/tutorials/editor/command_line_tutorial.html). It keeps the same game bytes, account checks, sandbox, and 60-second timeout. In the test account, run:

```sh
/bin/sh /private/tmp/untapped-sts2-transfer-01/retry_isolated_game_probe.sh
```

This refreshes only the account-owned original Python launcher helper and reuses the existing private session/data; it does not re-extract or modify the game. A new game-attempt directory preserves prior logs. Stay at the initial menu, leave prompts untouched, and report whether a visible window appears. Do not use the original setup script again: it intentionally refuses existing directories.

## Prepared reward-test step

The owner confirmed visible menu/settings/fullscreen navigation and fresh-looking data on the windowed retry. The timed shutdown is consistent with the 60-second supervisor; no crash was independently established. This confirms usable UI, not reader access.

A manual-play step is prepared but has not run. Once the owner agrees the bounded play step, `scripts/play_isolated_game.sh` (staged under `/private/tmp/untapped-sts2-transfer-01/`) refreshes only the original Python helper and runs the existing private game session with `--seconds 900 --manual-play`. The default remains 60 seconds. Both modes keep account, copy, signature, process-conflict and confinement checks. The owner controls play and pauses at one reward screen; the game is closed by its supervisor at the limit. No test account/profile is re-created.

The target-guarded companion is prepared privately as copy06, patched ASAR SHA-256 `e07df4f66c5918f11c9e8907a67783ae46c300ae8eda63ba3b9da5f0307d49c9`. Its exact `signing-proposal.json` preserves the five original entitlements and Hardened Runtime, with outer-only ad-hoc signing. It was unsigned/unlaunched at the proposal checkpoint; the subsequent approved signing and transfer are recorded below. When ready, a 45-second companion observation must run in the same test-account session, pinning the actual copied-game PID/user/executable. Manual Terms acceptance remains required. No game signing or debugging entitlement change is included.

## Approved reward observation

The owner approved copy06 signing, the same 45-second protected reader observation, and up to 15 minutes of isolated manual play. Copy06 signing and deep verification succeeded, retaining the original entitlements and Hardened Runtime. Signed executable SHA-256: `4e4a9e38726ca8fa160a68879e0db279d7fc95c363b95fd1cf8f0be3115b2ac1`. The transfer contains only the app, static preparation manifest and signing receipt; no profile/Terms/cache/log state.

1. In sts2test, keep Steam closed and run `/bin/sh /private/tmp/untapped-sts2-transfer-01/play_isolated_game.sh`. This starts the approved 15-minute supervisor. Play manually to a card-reward screen; do not choose a card. Keep the game windowed and tell the agent when ready.
2. When ready for the 45-second observation, open a second Terminal in the same account and run `/bin/sh /private/tmp/untapped-sts2-transfer-01/observe_isolated_reward.sh`. This installs the signed companion into a new private session on first use, verifies the transfer hash, and selects the sole exact copied game PID/user/path. A native guard rechecks identity before reader construction. Any Steam/extra-game process or identity mismatch stops the probe.
3. Review/accept Terms manually if desired. If the game covers the Terms window, minimize the game briefly, accept Terms, then restore the same reward screen promptly. Leave OS/security/sign-in prompts untouched and report them. Neither script accepts Terms or plays the game. Do not reopen either copied app through Finder or automation.
4. The reader closes after 45 seconds; the game closes at its 15-minute bound. Keep the Terminal reports, capture the visible reward choices for comparison, and report the result. Detection, native connection, traversal, reward match and overlay remain separate evidence gates. No compatibility success is claimed before this run.

The reader helper and four synthetic tests validate identity selection, ambiguity/Steam rejection, bounded dispatch and startup failure semantics. All 66 tests pass; shell and bootstrap syntax checks pass. The normal-account guard and game hash/signature checks remain in place. No long game run or signed-copy06 native observation has been executed by the agent.
