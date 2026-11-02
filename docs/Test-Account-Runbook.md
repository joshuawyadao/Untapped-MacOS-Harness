# Test account and first boot

The owner approved isolated setup and the confined 60-second first game probe. The owner has completed a first boot and confirmed fresh visible game UI; native reader/reward verification remains pending. The game-only transfer archive contains no saves, Steam settings, credentials, or companion profile.

1. In the MacBook's **Apple menu → System Settings → Users & Groups → Add User**, create a **Standard** account named `sts2test`. Choose the password privately. Stay in the normal account until preparation checks finish.
2. Quit normal STS2 and Steam yourself. When instructed, log out or switch into `sts2test`. Skip Apple Account sign-in and do not open/sign into Steam. Both test apps must ultimately run in this account's graphical session.
3. Open **Terminal** in `sts2test` and run the staged script:

   ```sh
   /bin/sh /private/tmp/untapped-sts2-transfer-01/run_isolated_game_probe.sh
   ```

   The script refuses other account names and existing test directories. It checks the game transfer hash, copies original harness code, extracts a source game copy, verifies the pinned game/signature, prepares a separate unchanged game copy, and launches it with `--force-steam=off --nomods` for at most 60 seconds. No administrator command or game signing is involved. Allow several minutes for extraction, hashing and signature checks before the game window opens.
4. During this first boot, remain at the initial menu. Stop if Steam, a sign-in, migration, imported progress, or an OS permission prompt appears. Do not approve prompts or start a run. The launcher stops its own game process group at the limit and stops if it detects an unexpected Steam/game process.
5. Keep the Terminal output and report the result here after returning to the original account. Logs stay under `~/UntappedSTS2GameSession/game-attempt-*` in the test account. We must verify fresh data paths, Steam-not-initialized state, and cleanup before gameplay; `isolation_verified` deliberately stays false in the launch report.

Writes are confined to the test account home/session. The game launch environment is constructed without inherited Steam overrides or credentials. The game child HOME now comes from the verified actual test-account home, never the inherited caller value. Earlier probes omitted it and used a relative user-data root. The comparison log must establish the new actual path. The policy denies the normal home and remote networking; finite dummy-file/socket probes passed, not a complete security audit.

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
2. When ready for the 45-second observation, open a second Terminal in the same account and run `/bin/sh /private/tmp/untapped-sts2-transfer-01/observe_isolated_reward.sh`. This verifies the signed transfer hash, selects the sole exact copied game PID/user/path, and extracts the same companion bytes into a fresh owned mode-0700 private tmp session for each observation. A native guard rechecks identity before reader construction. Any Steam/extra-game process or identity mismatch stops the probe.
3. Review/accept Terms manually if desired. If the game covers the Terms window, minimize the game briefly, accept Terms, then restore the same reward screen promptly. Leave OS/security/sign-in prompts untouched and report them. Neither script accepts Terms or plays the game. Do not reopen either copied app through Finder or automation.
4. The reader closes after 45 seconds; the game closes at its 15-minute bound. Keep the Terminal reports, capture the visible reward choices for comparison, and report the result. Detection, native connection, traversal, reward match and overlay remain separate evidence gates. No compatibility success is claimed before this run.

The reader helper and four synthetic tests validate identity selection, ambiguity/Steam rejection, bounded dispatch and startup failure semantics. All 66 tests pass; shell and bootstrap syntax checks pass. The normal-account guard and game hash/signature checks remain in place. No long game run or signed-copy06 native observation has been executed by the agent.

## Home-environment comparison after SIGBUS

Manual play stopped with exit -10 (SIGBUS) during early loading; no matching Apple crash report was found by the diagnostic exporter. No native stack establishes its cause. Separately, the launcher omitted HOME, and the game logged blank HOME, `./SlayTheSpire2`, and failed shader-cache creation. Upstream [Godot 4.5.1 path code](https://raw.githubusercontent.com/godotengine/godot/4.5.1-stable/platform/macos/os_macos.mm) falls back to relative paths when HOME is absent. The game's custom engine still requires a runtime comparison; this source does not prove the SIGBUS cause.

The child environment now restores the actual standard test-account home obtained from the OS account database after identity validation. It never inherits the normal account's HOME, redirects to a fake home, or changes the shell's HOME. Original-home denial, existing write scope, network denial and game bytes/signatures remain unchanged. Default game data is expected under the test account's Library/Application Support, with caches under its Library/Caches. Earlier relative test files are preserved and are not migrated, deleted or used as normal-account data. Fresh settings may appear again.

In sts2test, run `/bin/sh /private/tmp/untapped-sts2-transfer-01/diagnose_isolated_game.sh`. It refreshes the helper, runs 60 seconds, and exports that exact attempt's report plus bounded log excerpt automatically (excluding volume-inventory lines). Stay at the initial menu. Send the printed diagnostic file path and whether a visible menu appeared. Do not resume manual play until comparison results are checked.

## Helper-discovery layout comparison

The first home-rooted copy06 observation failed natively with SIGTRAP and Unable to find helper app, before bootstrap or any attachment result. The signed transfer archive matches all 333 source entries, including all four helpers, file modes and internal links. An inert Foundation lookup passed with and without the home-deny policy. No actual vendor root cause is established.

With test STS2 and Steam closed, run `/bin/sh /private/tmp/untapped-sts2-transfer-01/diagnose_companion_startup.sh` in sts2test. It checks the signed archive hash, extracts the same bytes into a fresh mode 0700 owned `/private/tmp/uc-sts2-UID-*` root, and performs a 45-second startup-only probe. It keeps the same outer home/write/network restrictions, signature and entitlements. Do not accept any OS/sign-in prompt. If Terms appears, leave it there; acceptance is not needed for this startup-only comparison.

The command refuses if any Steam/game process is present. It preserves the earlier home-rooted session and its logs; no profile/Terms state is transferred. It exports the exact report/stdout and inert bundle/helper metadata checks both outside and inside that attempt's policy. Send the printed diagnostic-file path and whether a window appeared. This is a layout diagnostic based on earlier successful private-tmp startup, not a proved fix or native-reader result.

The reader helper now accepts only private owned 0700 sessions in its test home or a canonical direct child of `/private/tmp` with its UID-bound `uc-sts2-UID-` prefix. Symlinks, other roots, wrong owners/modes and empty namespace suffixes are rejected. The default reward mode still requires the sole exact game PID/user/path; startup-only supplies no target and the existing native guard refuses any attachment if a game appears after preflight.

## Temporary-layout startup passed

The owner-run startup-only comparison reached ELECTRON_READY and TERMS_LOGGED and ended at its 45-second limit. The exported diagnostic `/private/tmp/sts2test-companion-startup.0avbf51j.json` identifies session `/private/tmp/uc-sts2-502-hchi62ym`; inert helper checks passed outside/inside policy. The owner confirmed the visible page was the Untapped companion window. This establishes startup in that layout; the exact mechanism of the earlier home-rooted failure remains unconfirmed.

The reward-observation script now creates a fresh short private tmp root for every run, using the same signed archive, owner/mode checks and outer policy. It exports an exact report, bounded stdout/Core log and the existing whitelisted events to a `sts2test-reward-probe.*.json` file after cleanup. The diagnostic path prints only after the 45-second probe and cleanup finish. Profile/Terms state and prior sessions are preserved without migration; each fresh observation requires the owner's manual Terms choice.

Restart the approved 15-minute game session with the play script, reach a reward without choosing a card, then run the observation script in another Terminal in the same account. Accept Terms manually if desired, briefly minimize the game if it covers that window, then restore the reward promptly. Send the diagnostic path and a photo of the visible choices. Actual detection, connection, reward match and overlay remain untested.
