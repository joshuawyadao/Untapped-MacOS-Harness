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

## Copy07 identity check retry

Copy06 reached Core initialization and detected the window, but our guard's `/bin/ps` launch was denied before reader construction. Copy07 uses an original unprivileged same-user metadata helper under the unchanged outer policy. Targeted observations now need working Apple command-line tools (`/usr/bin/clang` and SDK) in the test account; compiler errors stop before launching the companion. Do not automatically install tools, answer license prompts or approve OS dialogs.

The updated observation/startup scripts expect `companion07.tar` and its checksum and refresh the four original helper sources. Copy07 signing and live transfer staging are now complete following explicit owner approval. The archive checksum and all archived files/symlinks were verified; the source/script refresh matches the repository. Copy07's exact outer-only signing proposal retains the five original entitlements and Hardened Runtime. That exact signing scope was approved and executed; the transfer contains app/manifest/receipt and original harness sources without any profile, Terms, logs or credentials. Existing copy06 transfer remains available pending that decision.

After that preparation, the already-approved manual-play step can be used to reach another reward. Keep choices visible, run the protected 45-second observer in the same test account, review Terms manually, and provide the exported diagnostic path and card image. Do not infer attachment from window detection. Game signing and debugger-entitlement changes remain excluded.

## Original-process attachment diagnostic

Copy07 reached the real native connection attempt, which returned false. The controlled original-fixture matrix ran twice in UID501: target access was denied without get-task-allow and allowed with it, inside/outside the existing outer policy. Repeat in the standard `sts2test` graphical account to check that account's authorization context before proposing game signing:

```sh
/bin/sh /private/tmp/untapped-sts2-transfer-01/diagnose_attachment_access.sh
```

No gameplay, reward screen, Terms acceptance or sign-in is needed. The script signs/launches only three fresh original fixture binaries (two targets and an inspector), queries task ports for its generated same-user targets, reads no target memory, stops all fixtures, and prints a `Diagnostic file` path for sharing. Compilation/signing/probe errors stop the experiment; do not approve any unexpected OS or developer-tools prompt. Send the path or exact error if one occurs.

This operation does not sign, launch or change either game/companion copy, and does not enable any global debugger/protection setting. A target-process entitlement difference in the fixture test supports a future separately approved debug-enabled game copy; it cannot establish that the real reader or reward geometry works.

## Separate debug-game copy proposal

UID502 confirmed the original-fixture entitlement distinction. A new unsigned copy is now prepared at `/private/tmp/untapped-sts2-debug-game-01/SlayTheSpire2.app`, byte/file-mode/symlink matched against the complete original tree pin. Its exact JSON proposal is `/private/tmp/untapped-sts2-debug-game-01-proposal.json`. It proposes outer-only ad-hoc signing, preserving Hardened Runtime and the original four entitlements, adding only `com.apple.security.get-task-allow`. This lets debugging tools acquire this copy's task port while it runs. The installed game, existing isolated game, nested code and global protections remain unchanged.

**Approved and executed:** the owner approved the exact signing and bounded test sequence. The following signing command is recorded for review; do not repeat it on the already-signed session:

```sh
python3 -m harness.game_debug sign /private/tmp/untapped-sts2-debug-game-01 --approve-debug-game-signing
```

After approval, verify the signed copy and archive only `SlayTheSpire2.app`, `debug-game.json` and `debug-game-signing.json`, with checksum and per-entry transfer checks. Original harness sources and the three scripts are now staged following successful signature/tree/archive verification. No profile, saves, Terms or credentials belong in the transfer. The existing original game archive is preserved; the observer now supports explicit debug-copy selection.

The future test-account workflow is: run `install_debug_game.sh` once (refuses an existing destination), then `play_debug_game.sh` for a 60-second boot check. For the approved reward experiment, `play_debug_game.sh --manual-play` allows up to900 seconds, and `observe_isolated_reward.sh --debug-game` selects only that separately signed copy for the protected45-second observation. Terms are reviewed manually, and the owner supplies the visible cards plus diagnostic path. Never open either copied app directly in Finder.

The destination is `/Users/sts2test/UntappedSTS2DebugGameSession`, distinct from the unchanged earlier game copy. Both use the test account's same existing Godot user data; this does not create another fresh save profile. Normal-account saves remain inaccessible under the existing game policy. The new entitlement does not imply successful state reading or overlay; those remain separate evidence gates.

Signed transfer is ready as `debug-game01.tar` with verified checksum. In `sts2test`, close Steam and any running game, run `/bin/sh /private/tmp/untapped-sts2-transfer-01/install_debug_game.sh`, and after successful installation run `/bin/sh /private/tmp/untapped-sts2-transfer-01/play_debug_game.sh`. The first boot check closes at60 seconds; this expected stop is not itself a crash. Report whether the main menu appears and retain the Terminal result. The900-second play and45-second observer steps are already approved, but their runtime evidence follows a successful boot check.

## Retry after transfer permission mismatch

The first debug-game install stopped during source verification because tar extraction under private umask077 changed archived file modes. The fixed installer preserves those recorded modes with tar -xpf inside a private0700 root, retaining the full receipt/signature guard. The signed archive and signing approval are unchanged. Re-run the same `install_debug_game.sh` command; it creates a fresh extraction and preserves the failed one. Only after installation succeeds, run `play_debug_game.sh` for the approved60-second boot check. An existing debug-game destination still causes a refusal rather than overwrite.

## First debug-copy reward result and remaining evidence

Installation and the60-second menu check succeeded, followed by a real native reader connection and reward event in the approved manual-play/45-second observation. Haze, Ricochet and Infinite Blades match the photo, all upgrade level0 and in the correct order. The owner clarified that no overlay appeared on the game screen. Do not repeat an identical run merely to reconfirm those IDs.

Full geometry is still incomplete: current capture omits native scaleX/scaleY, and the phone photo crops the game viewport. A future scale-complete companion preparation/signing proposal and full-viewport digital screenshot are needed for an independent rendered-bounds comparison. Use the game content area, not desktop or title-bar coordinates. Never use the captured reader values as their own expected answer.

The vendor reward UI is statically login-gated, and public-data fetching has no cache under the retained offline policy. Full UI work needs a separately reviewed isolated account/data plan; do not sign in, enable networking, approve prompts or bypass gates as part of this completed observation. Settings/property-read errors also need separate compatibility investigation. Existing signing approvals do not authorize those new account/network actions.

## Approved controlled sign-in probe (first attempt failed)

The owner approved the [controlled-access plan](Controlled-Access-Plan.md) and exact private copy08 signing/access proposals. Outer-only signing and deep signature/entitlement/payload checks pass. The signed profile-free archive, checksum and original launcher/helpers are staged; exact-mode extraction was verified. The first live probe subsequently failed at token HTTP403; the read-only follow-up below is the current next step.

In the standard sts2test account, close Steam and every game copy, then run:

```sh
/bin/sh /private/tmp/untapped-sts2-transfer-01/controlled_sign_in.sh
```

This first probe is login-only. A later `--observe-debug-game` mode can observe only the existing verified debug game. The attempt is at most300 seconds and at most45 seconds after genuine sign-in succeeds.

The companion does not open a browser: its sign-in control writes a private manual-sign-in URL file and the supervisor prints that file's location. Read it in a second test-account Terminal and open the URL yourself in that account's browser; finish credentials/consent manually. Do not share that URL, raw logs/settings or callback material. The new Diagnostic file export contains only safe harness status/events/cards and route counters. Existing raw-log observation exports must not be used after authentication.

Account/token and public JSON/commentary/tier routes are permitted by the approved gateway; stats/predictions, history/uploads, telemetry and artwork are blocked. The vendor consent scope is companion:full-access even though companion traffic is filtered; browser website traffic is outside that filter. The separate settings-property error can still block overlay target resolution, so successful login/data loading is not proof that the overlay appears. Send only the printed sanitized Diagnostic file path after this run; retain a failed/timed-out result for review before another attempt.

## Read the saved token HTTP403 without sharing raw logs

The first probe's safe export records one upstream oauth_token403, no authenticated event, no local allowlist rejection and complete cleanup. In the same sts2test account, run this read-only command against that saved attempt:

```sh
/bin/sh /private/tmp/untapped-sts2-transfer-01/classify_sign_in_error.sh /private/tmp/uc-sts2-502-b6hogsud/outer-attempt-64jcgjm3
```

Send only the printed `Diagnostic file: /private/tmp/sts2test-auth-error.…json` path. This original helper reads two bounded saved logs privately and exports fixed error categories/booleans only. It opens no browser/app and makes no network requests. It does not modify the saved attempt, gateway, adapter or signed copy08. An unclassified result is valid evidence; do not paste raw errors or retry login to fill the gap.
