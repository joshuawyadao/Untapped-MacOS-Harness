# Verification and reward milestone

For the November 10, 2026 starting-relic check, see [Starting-relic badge investigation](Starting-Relic-Diagnosis.md). The owner confirmed three visible named-tier badges (“Inconsistent”) after native IDs, tier coverage and actual DOM rectangles were verified. No rendering patch was required for that observation.

This record distinguishes static inspection, startup, game detection, reader attachment, state reading, and overlay display. Each requires separate evidence. The pinned user-supplied companion was `3.12.3-latest` with `app.asar` SHA-256 `ca3a2e6a6f728b2d635abfc70a5434d4107438b8d801a650357989e8442d798c`.

| Milestone | Result through the November 3, 2026 observation | Evidence or next check |
| --- | --- | --- |
| Static inspection/preparation | Verified | Exact companion pins, guarded patches and binary checks reproduced. |
| Offline policy | Smoke-tested and retained | Bounded runs retain home/write/network confinement; finite tests are not a complete audit. |
| Companion signing/startup | Verified after approval | Copy09's owner-run report reaches Core initialization with valid settings and overlay lifecycle events; original companion entitlements/Hardened Runtime retained. |
| Separate debug-game copy | Installed; menu confirmed | Exact approved game-copy signing adds only get-task-allow; owner confirmed menu during the60-second boot check. Installed game and normal saves unchanged. |
| Native window detection and connection | Observed | Ordered window-detected, attach-attempt and reader-connected events precede the reward. |
| Authenticated reward identities/upgrades | Match photo | Latest09 reward: COLLISION_COURSE0, ASTRAL_PULSE0 and CELESTIAL_MIGHT0 in order; earlier08c also matches its three photographed cards across42 events. |
| Rendered reward geometry | Incomplete | Native scales are now captured; independent full-viewport geometry remains absent. The phone photo crops the viewport. |
| Account and public data | Observed on08c | Genuine auth, account/token200, STS2 exchange200, six public JSON200 and eight tier-resolution200 responses. This does not establish every feature/render gate. |
| Vendor overlay | Visible badges confirmed on09 | Owner photo shows badges beneath Collision Course, Astral Pulse and Celestial Might; report matches IDs/order and settings/show events. Labels appear as ?-Tier, so actual ratings remain unresolved. |
| Advice, stats, tracking and broader compatibility | Unverified | Settings now recover on09. Actual tier values, broader UI behavior, long sessions and normal Steam/Cloud progress remain separate checks. |

At the initial copy04/05 checkpoint, preparation made no signing change; the outer signature was later changed only with explicit owner approval. No entitlement was added. During the protected runs no game was launched and no save was read. The owner manually accepted Terms on November 2; no account login or run upload was authorized or observed. Copy04 attempted anonymous-token acquisition, which failed under the offline policy; the adapted copy05 reaches logged Core initialization without those requests. Other metric requests still fail under the offline policy. The separate extra-launch incident below has unknown native profile effects. Forty-six synthetic tests passed, including Node VM execution of the original bootstrap against stubs, ten mocked signing tests, six startup-diagnostic tests, seven approved outer-launch tests, and three offline-authentication tests. Vendor code and native modules were not executed in that suite. The CI test job checks portable harness behavior and repository hygiene, not macOS game compatibility.

Before approved signing, the locked desktop prevented UI inspection but was not the startup cause. The unlocked inventory still showed no companion window. A process sample contained only `_dyld_start`, a 96 KiB footprint, and no loaded-image listing; a minimal Electron run-as-Node probe also stalled then. The OS log explicitly identified Gatekeeper rejection and assessments identified an invalid resource seal. After approved signing, the same runtime diagnostic succeeds. Nested helpers/frameworks verified. No OS warning was approved or bypassed.

## Companion-only signing

The owner approved re-signing **only the outer companion bundle** in copy04, then separately approved the same operation for copy05 after the offline credential adaptation. Both executions succeeded, retaining Hardened Runtime and the five existing true entitlements: debugger, JIT, unsigned executable memory, DYLD environment variables, and disabled library validation. That companion-only scope permits no new entitlement or recursive signing. The later game-copy entitlement experiment was separately approved and is recorded below; it does not broaden the companion signing scope.

The reviewable command produced by `signing-proposal` has this form:

```sh
/usr/bin/codesign --force --sign - --options runtime --timestamp=none \
  --entitlements /private/tmp/untapped-sts2-session/companion-entitlements.plist \
  /private/tmp/untapped-sts2-session/Companion.app
```

Only after explicit owner approval, `python3 -m harness.cli sign-copy /private/tmp/untapped-sts2-session --approve-ad-hoc-signing` executes that operation, verifies both architectures' entitlements and the nested code, and writes `signing.json`. Launch accepts the specific resulting executable hash while retaining its ASAR/framework/native-reader guards and re-verifying the signed copy. The receipt records the local operation; it is not an authorization credential or vendor trust.

Ad-hoc signing replaces Untapped's Developer ID identity for that copy and provides no vendor notarization. This signed copy executed and reached Electron readiness without an OS exception. No warning exception, quarantine removal, or global protection change was performed. Roll back by discarding only the disposable session. Apple's [code-signing guidance](https://developer.apple.com/library/archive/technotes/tn2206/_index.html) distinguishes signing nested code from recursive verification.

## Approved single-layer experiment

The signed copy's failure is now reproducible after Electron readiness. `stdout` reports a failed socket directory and child `sandbox initialization failed: Operation not permitted`; the vendor log incorrectly infers an existing instance from the failed lock. A minimal Node-mode diagnostic on the same signed executable succeeds. The runtime identifies Electron 37.10.3 and Chromium 138.0.7204.251.

Chromium's [macOS temp-path implementation](https://raw.githubusercontent.com/chromium/chromium/main/base/files/file_util_apple.mm) checks `MAC_CHROMIUM_TMPDIR` before `NSTemporaryDirectory`; the CLI now redirects that to a short session-local `t/` directory. A synthetic AF_UNIX bind was denied by the original IP-only policy. A proposed session-path-only socket allowance passed positive/negative probes: inside-session bind allowed; outside-session socket connect, remote-IP connect, real-home read, and outside write denied. IP binding behavior did not change; those finite probes do not establish every inbound-network property.

The independent child failure has a different mechanism: [Electron's exact helper entry point](https://raw.githubusercontent.com/electron/electron/v37.10.3/shell/app/electron_main_mac.cc) initializes Chromium's Seatbelt policy, and the installed `MacOSX27.0.sdk/usr/include/sandbox.h:25–27` documents that a process already in a sandbox cannot initialize another profile this way. Redirecting temp files or allowing private sockets does not resolve it.

The owner separately approved a 45-second command for the **same already signed disposable app**, with a fresh empty profile, `MAC_CHROMIUM_TMPDIR` inside its session, session-path-only Unix IPC, the outer offline/home/write confinement retained, and **`--no-sandbox` for Chromium child processes**. The children inherit the outer policy, but lose Chromium's separate process sandbox. This is a security tradeoff, not equivalent protection. No global protection, installed game, saved run, or remote network access is included.

The exact command/environment/policy were prepared privately in the session's `next-launch-proposal.json` and `offline-next-proposal.sb`, checked before execution, and then run under the process-group supervisor. It remained until its 45-second limit, and the runner stopped its process group. No proprietary material or private profile belongs in Git. It uses the following command form, with the profile argument pointing to a new empty profile:

```sh
/usr/bin/sandbox-exec -f /private/tmp/untapped-sts2-session/offline-next-proposal.sb \
  '/private/tmp/untapped-sts2-session/Companion.app/Contents/MacOS/Untapped.gg Companion' \
  --user-data-dir=/private/tmp/untapped-sts2-session/next/profile --no-sandbox
```

The raw command must run through the bounded process-group runner with a 45-second timeout and group cleanup; it has no timeout by itself. The flag was used only after explicit separate approval for this copy. The default `launch` CLI still uses both layers. `launch-outer --approve-outer-sandbox-only` now provides a tested, repeatable bounded implementation: each attempt uses a new private profile, re-verifies the signed copy and fixed payload hashes, retains outer restrictions, and records its own manifest, logs, launch result, and report. Terms acceptance and live gameplay still have their own boundaries.

## UI observation incident and current boundary

The protected attempt logged `[Core] Showing Terms of Service`, but the CUA app-selection call timed out after the 45-second runner ended. A subsequent exact-path process check found one new main process and two helpers for the disposable copy; helper arguments pointed at the normal companion profile. All three were stopped once detected; no exact-copy process remained. Timing supports a CUA/LaunchServices reopen, but does not prove its provenance.

This extra instance was outside the protected runner. The compiled bootstrap would reject missing harness environment before importing vendor Sentry/Core code, but native Electron/Chromium initializes earlier. Default browser cache/preferences or native-helper activity therefore cannot be ruled out. No evidence establishes account access or uploads. The normal profile was not inspected or deleted, and no claim is made that it remained untouched. No game was launched or terms accepted.

Do not use app-opening or bundle-ID selection APIs to inspect bounded probes. Use the CLI supervisor, non-launching inventory, and manual interaction. Terms acceptance remains the owner's action; the sandbox approval alone does not authorize accepting terms or starting gameplay.

## Manual Terms review

On November 2, the owner confirmed readiness for manual review. The existing `launch-outer` CLI reverified the same signed disposable copy and ran it for 45 seconds with a fresh private profile and unchanged outer restrictions. The owner accepted Terms in that window: `profile/config.json` records `acceptedTOS=true`, and the vendor log records Terms of Service have been accepted/continuing initialization.

Evidence is retained privately at `/private/tmp/untapped-native-sts2-poc-04/outer-attempt-mn7n35o2`. At that checkpoint it was the only attempt known to record acceptance; the later copy05 acceptance is recorded below. The CLI always creates a fresh profile; repeating it does not inherit acceptance. Do not seed acceptance into another profile or inspect the normal companion profile to bypass this distinction.

After acceptance, vendor startup repeatedly attempted anonymous upload-token acquisition, which failed with `getaddrinfo ENOTFOUND` under the offline policy. Core logged Loaded all accounts, but not Fully initialized before timeout. Events contain only bootstrap and ready. The status report therefore still says `TERMS_LOGGED`; that coarse label does not undo the separate acceptance evidence or establish full initialization. No game detection, attachment, reward, overlay, or recommendation success follows from this run.

The process-group runner reached its limit and exited successfully; the exact-copy process check found no remaining processes. No app-opening observation API was used. No installed game, saves, normal companion settings, remote network permission, or signing configuration was changed during this attempt. Further work must preserve the offline boundary and establish the game-profile/save strategy before gameplay.

## Offline credential acquisition

Pinned-source inspection explains the delay: Core awaits authentication initialization, account integrity checks, and onboarding before STS2 construction. Each can request an anonymous token when no credentials exist. Three retry waits of 1, 4, and 9 seconds per acquisition can consume roughly 42 seconds before request latency. The five-second account timeout starts after the authentication awaits, so it does not bound them. A longer probe might advance naturally, but requests have no explicit request timeout. This is an offline startup dependency, not a demonstrated reader failure.

Preparation now adds a guarded Services-chunk change: `ensureLocalCredentials()` returns `{ authenticatedCredentials: {}, anonymousCredentials: null }` before credential I/O or token acquisition only when `UNTAPPED_HARNESS_OFFLINE=1`. The regular startup sequence continues with authentication unavailable. Existing consumers still report no logged-in user, no token, no account feature, and no entitlement. Terms and the native reader are unchanged, and the outer network deny remains necessary because other vendor paths may attempt network requests. Missing downloaded metadata, statistics, and account features remain outside this offline proof of concept.

`python3 -m unittest discover -s tests -p test_offline_auth.py -v` initially failed on the old code because the synthetic method acquired a token and the Services entry had no anchor guards. All three tests now pass: they execute synthetic JS with no credential/token I/O offline, verify repeat calls and ordinary behavior outside exact offline mode, and reject missing/duplicate anchors. The full suite passes 46 tests. No real token or credential is used.

A fresh unsigned copy was prepared at `/private/tmp/untapped-native-sts2-poc-05/Companion.app`. Full packed-entry comparison found exactly three changed entries; their JavaScript syntax checks passed. At preparation, every other packed entry, executable, framework, native reader, and Info.plist was unchanged; the outer executable was later signed only with approval. The source ASAR hash remains pinned; the new patched ASAR hash is `e102b9c5c4369e4d995a7d5ebf1e06a4f81aa042f12172d729e0886c373d3e4f`. No profile or accepted-Terms state was copied into it, and the read-only source disk image was detached after preparation.

The exact outer-only signing proposal is private at `/private/tmp/untapped-native-sts2-poc-05/signing-proposal.json`, with the same five original entitlements verified on both architectures and Hardened Runtime retained in the proposed command. At the proposal checkpoint this copy was unsigned/unlaunched; the owner subsequently approved and executed it as recorded below. Synthetic tests and syntax checks do not establish native compatibility.

## Approved copy05 execution

The owner explicitly approved copy05's signing proposal and another 45-second protected startup. Outer-only signing succeeded; deep strict verification, both original entitlement sets, and fixed native/framework/ASAR hashes passed. Its private `signing.json` records signed executable SHA-256 `daffa1ea0eb5fbb20eb7035f43a5d9224787feef3c566b2dbd7826cc353c866e`. No new entitlement, nested signing, game change, or global protection change was included.

The supervised run created `/private/tmp/untapped-native-sts2-poc-05/outer-attempt-jft7ntme`. It recorded bootstrap and Electron ready and logged Showing Terms of Service. The fresh private config had no `acceptedTOS` value after the run, and no accepted-Terms log, full initialization, detection, attachment, or reward event was recorded. At that checkpoint manual acceptance belonged to copy04's separate private profile, and the offline credential branch still lacked a post-Terms native check. Absence of token retries while Terms was pending did not validate it; the subsequent successful initialization is recorded below.

The runner reached its 45-second limit, cleaned up its process group, and an exact-copy process check found no remaining copy05 processes. No app-opening inspection API was used. Signing and the same protected mode for this copy are already approved. The 46-test suite was previously passing; this execution changes private artifacts and documentation only, so no new test case or repeated suite run is needed.

At the owner's requested readiness retry, fresh private attempt `/private/tmp/untapped-native-sts2-poc-05/outer-attempt-bs1oj8lo` again logged Terms and recorded only bootstrap/ready. It reached the 45-second limit with no `acceptedTOS` value or post-Terms milestone, and no exact-copy processes remained after cleanup. The owner confirmed seeing Terms with an Accept button, then clarified that Accept had not been clicked. This verifies manual visibility; it is not evidence of a broken acceptance action.

## Successful offline Core initialization

After that clarification, the same approved copy/mode was reopened for 45 seconds with fresh private attempt `/private/tmp/untapped-native-sts2-poc-05/outer-attempt-7g7qo6mz`. The owner accepted Terms manually. Its config records `acceptedTOS=true`; Core logs Terms accepted and Fully initialized in the same second. There are zero anonymous upload-token acquisition/retry lines. Status reports `CORE_INITIALIZED_LOGGED`, with no recognized startup blocker.

Other metric requests failed with `ENOTFOUND` under the unchanged offline policy. Empty authentication does not disable every attempted vendor network operation, and no authenticated functionality follows from this startup result. The outer confinement remains necessary.

The time limit was reached, the process group was cleaned up, and no exact-copy processes remained. Diagnostic events contain only bootstrap/ready: no game was launched/detected, no reader connection or reward was observed, and no overlay behavior was verified. This is a successful offline Core-startup milestone, not native game compatibility.

## Isolated-game planning evidence

The owner chose to plan an isolated profile before gameplay. The resulting [plan](Isolated-Game-Plan.md) recommends a dedicated standard local macOS test account with both apps in the same graphical session, fresh data, and no Steam initialization. This is an isolation recommendation, not proof that a lighter same-account solution is impossible. No account, game copy, game launch, save inspection, Steam change, or game signing was performed during planning.

Read-only inspection of the installed distribution found version `v0.107.1`, commit `59260271`, in `Contents/Resources/release_info.json`. The arm64 assembly `Contents/Resources/data_sts2_macos_arm64/sts2.dll` has SHA-256 `e7ceb80669bfaf5c8fccabaa126ae2bb283aba514be5b5b55612579cfd285f18`. Its static CLR metadata/IL establishes:

| Finding | Static location |
| --- | --- |
| `--force-steam=off` returns before Steam initialization; its log misleadingly calls this editor mode | `NGame.<InitializePlatform>d__162.MoveNext`, token `0x06009479`, IL `0x1b–0x99` |
| `--nomods` skips mod initialization | `ModManager.<Initialize>d__22.MoveNext`, token `0x0600bb2b`, IL `0x47–0x64` |
| Arguments accept `key=value` or `key value`, trim leading hyphens, and read engine command-line args | `CommandLineHelper`; pass game flags before any `--` separator |
| Steam save-store wrappers are conditional on Steam having initialized | `SaveManager.ConstructDefault`, token `0x06000721`, IL `0x3a–0xa8` |
| No verified custom save-root flag; `save_dir=` is a logging literal | `UserDataPathProvider` derives `user://` paths; release/non-Steam data uses `default/<localId>/profileN` |

These are static results. A future first-boot probe must confirm actual data paths, Steam absence, file confinement, and cleanup before gameplay. [Godot documents](https://docs.godotengine.org/en/4.5/tutorials/io/data_paths.html) platform user-data locations; those defaults do not become isolated merely by moving the game bundle. [Valve documents](https://partner.steamgames.com/doc/features/cloud?l=english) client-managed and API Cloud sync, and its [restart API](https://partner.steamgames.com/doc/sdk/api%20?l=english) can relaunch the installed library copy. Neither copying the app nor quitting one supervised process establishes Cloud isolation by itself.

Companion static tracing also separates memory from files. Core's save watcher (`Core-tWQs6NtS.js`, lines 24642–24759 in the private inspection) resolves save/history under the companion's redirected home. Reward fields come from live card/control objects (`ScryRuntime-Bw9hEAKx.js`, lines 11965–12164); even settings/SaveDir come from process objects. Leave file-based history empty for the first reward test. The matcher is supplied only the owner name Slay the Spire 2, without a bundle-path restriction, and does not track PID changes while a matching window remains. Require exactly one expected game process and independent PID/path/user verification. No cross-user attachment behavior has been established.

## Commands and private evidence

Use the commands in the [README](../README.md). `inspect` prints pinned-source observations. `prepare` creates `manifest.json` inside a fresh private session. `launch` is single use per session; it returns a nonzero status if `ready` is not observed or a known startup blocker is logged. `startup_blockers` distinguishes socket-directory and child-sandbox errors. A recorded nonzero process exit also makes the CLI fail, even if an earlier ready event was emitted; a bounded timeout is recorded separately. `companion_initialization` reports only observed Core/terms log milestones, which still need visual confirmation. `ELECTRON_READY` means Electron reached its readiness callback; it does not prove Untapped's UI or services finished initializing. `status` reads only that session's private events and log. A manifest records static preparation, not proof of startup. Do not commit or publish session logs, events, screenshots, or a modified companion copy without reviewing personal data and third-party rights.

Before a real reward experiment, establish a game-profile, save, and Steam Cloud strategy. Do not copy or symlink actual saves by default. No signing, debugger entitlement, or system protection change should follow from this record without a concrete failure and a specific reviewed proposal.

## Reward comparison contract

A later real screen can be transcribed into a private JSON file, with visible cards from left to right and normalized coordinates (`0`–`1` relative to the game screen):

```json
{
  "cards": [
    {"id": "EXAMPLE_CARD_A", "upgradeLevel": 0, "cx": 0.25, "cy": 0.5, "width": 0.12, "height": 0.2},
    {"id": "EXAMPLE_CARD_B", "upgradeLevel": 1, "cx": 0.75, "cy": 0.5, "width": 0.12, "height": 0.2}
  ]
}
```

These IDs are synthetic and do not assert actual game identifiers. Run `python3 -m harness.cli compare-reward /private/tmp/untapped-sts2-session /private/tmp/expected-reward.json --reward-index 0`, choosing the zero-based reward event to inspect. The tool sorts cards by `cx`, then `cy`, requires exact count/ID/upgrade level, and allows at most `0.03` absolute difference in each normalized center/size coordinate. It also requires preceding bootstrap, ready, window, attach-attempt, and reader-connected events. A comparison can validate the one-screen reader milestone; overlay positioning, tier lists, statistics, and adaptive recommendations need their own checks.

## Isolated launcher preparation

Owner approval now covers isolated setup and the planned first game launch. Implementation and transfer staging are ready; account creation/login and the native run have not been completed. See [the runbook](Test-Account-Runbook.md). The normal-account CLI refusal was exercised, and dummy-file/socket policy probes passed private writes versus denied original-home reads, outside writes, and remote connections. All 59 portable tests pass. No native game was launched or signed, and no save/profile was imported. The new target guard is implemented in source but has not been packaged/signed into a companion copy. The previously verified offline startup belongs to copy05's earlier patch set.

## First native game probe: menu initialization logged, visibility pending

The owner ran the account script in sts2test. The photo report shows the pinned copy prepared with game_modified=false and the 60-second limit reached, with isolation_verified=false. The owner saw no menu. A deliberate filtered log export confirmed Steam initialization skipped; user data directory `./SlayTheSpire2` (relative to the confined session cwd); intended no-Steam/no-mods arguments; and both main-menu essential/complete load milestones. Shader-cache creation failed, but did not prevent those later log milestones. Shutdown static-string errors do not independently establish a startup failure.

The next approved bounded retry requests explicit windowed mode, position/size, and always-on-top. All 59 tests pass, including the updated launch-command check; shell syntax passes. Actual UI visibility, cleanup confirmation, and full isolation verification remain pending. No game signature, entitlement, network rule, or 60-second limit changed.

## Visible fresh game confirmed; guarded reward test prepared

The owner reported that the windowed retry showed the main page, allowed fullscreen/settings/back navigation, then closed, and looked like fresh game data. Together with the prior Steam-skipped/private-relative-data-root log and bounded launcher report, this advances UI/fresh-profile evidence. The close is consistent with the 60-second cutoff; no crash or complete file-isolation audit was established from that report. Native reader attachment, reward IDs/upgrades/positions and overlay remain untested.

An opt-in manual-play limit of 900 seconds is now implemented; default probes remain capped at 60. All 62 synthetic tests pass, including invalid-boundary, CLI-dispatch, and long-mode timeout cleanup coverage. No long native run occurred.

Fresh copy06 is prepared from the pinned pristine companion, with the target identity guard included. Exactly three packed JS entries differ; all pass Node syntax checks. Every other packed entry and fixed executable/framework/native reader/Info.plist hash is unchanged. Patched ASAR SHA-256: `e07df4f66c5918f11c9e8907a67783ae46c300ae8eda63ba3b9da5f0307d49c9`. Its private signing proposal verifies both original entitlement sets and proposes outer-only ad-hoc signing with Hardened Runtime retained. Signing and launch have not occurred. The source image was detached after preparation.

## Approved copy06 signing and reward-test staging

The owner explicitly approved copy06 signing, the protected 45-second reader probe and 15-minute manual-play step. Copy06 outer-only ad-hoc signing succeeded; deep verification and both original five-entitlement sets passed, Hardened Runtime retained. Its signed executable hash is `4e4a9e38726ca8fa160a68879e0db279d7fc95c363b95fd1cf8f0be3115b2ac1`. No nested/game code was re-signed and no entitlement was added.

A profile-free signed transfer and test-account observation helper are staged. Four new synthetic tests bring the suite to 66 passing cases. The helper checks standard account, private session, sole exact copied PID/user/path and Steam absence before dispatching the guarded 45-second launch. Native copy06/game-reader observation remains pending on the owner's paused reward screen; successful signing/preparation is not attachment or reward evidence.

## Manual-play SIGBUS and home correction

The owner reported -10 (SIGBUS), rather than a timer expiry, in manual-play attempt `game-attempt-b3v3jv6c`. Its exported log ends during early asset/localization loading, before a menu milestone. No matching copied-game Apple crash report was found by the owner-run exporter. Earlier timed probes' shutdown string warnings are not evidence for this failure's cause. No new game or reader run has been attempted since.

A separate verified configuration defect was corrected: HOME was absent from the game environment, matching its relative data path and shader-cache warning. Child HOME now uses the verified actual test-account home; inherited normal-home/Steam/preload overrides are excluded. The existing launch regression failed with missing HOME before correction and passes afterward with a deliberately wrong parent HOME. All 66 tests pass; diagnostic shell/embedded export syntax passes. Sandbox, game signature/bytes and account requirements remain unchanged. The 60-second runtime comparison and SIGBUS resolution are unverified; old private relative data is preserved.

## First copy06 native observation: helper lookup failure

The owner executed the observation script while at a card reward. The signed transfer SHA check passed, but the companion returned -5 (SIGTRAP) with only FATAL Unable to find helper app. No bootstrap, Electron ready, Terms, window-detection, attachment or reward event was observed. This is an Electron native startup failure, not an established task-port or reader-compatibility failure.

The archive audit found 333 matching entries (178 directories,141 regular files,14 internal symlinks), matching all regular hashes/modes and helper names/Info.plists/executable bits. It does not prove target extraction. A separate inert Foundation lookup under the same home-deny/session-allow policy succeeded; a targeted short system-log search found no matching denial. These tests do not identify the vendor failure's root cause.

A same-signed-bytes comparison in a short private tmp root is prepared, with unchanged outer restrictions and a 45-second startup-only bound requiring Steam/game absence. The diagnostic adds inert target-layout checks inside/outside the exact policy and exports their results automatically. Three new synthetic cases bring the suite to 69 passing tests; shell and embedded snapshot syntax checks pass. Actual startup in this layout remains pending on the owner, and no app/game signing or protection change occurred.

## Short private-tmp startup confirmed

Exported diagnostic `/private/tmp/sts2test-companion-startup.0avbf51j.json` records ELECTRON_READY, TERMS_LOGGED, no recognized startup blockers and the 45-second limit reached in `/private/tmp/uc-sts2-502-hchi62ym`. The owner confirmed the visible page was the companion window. All four helpers were present with mode 0700 in inert metadata checks both inside and outside the exact policy. Native helper discovery succeeded in this location; the underlying cause of the earlier home-rooted failure is still unconfirmed. No game was present for this startup-only comparison, so no attachment or reward result follows.

The observation script now uses fresh private tmp roots and automatic report/event/log export. The signed bytes, entitlements, outer restrictions, UID/path/PID checks and 45-second bound are unchanged. All 69 tests and shell/embedded-Python syntax checks pass; no new native reward observation has yet occurred.

## Copy06 window detection and copy07 guard replacement

The owner-run reward export confirms Electron readiness, Core initialization and window-detected (PID 32398). The guard then throws `spawnSync /bin/ps EPERM` before reader construction; attachment/state/reward remain untested. `/bin/ps` is setuid (4755); its execution fails in a same-policy inert reproduction. A byte-identical non-setuid temporary copy was killed by OS validation and discarded without re-signing. No game entitlement failure was observed.

The replacement original C helper uses `proc_pidinfo`/`proc_pidpath` for same-user metadata only. Its production build queried an inert same-user target under the unchanged outer policy, including a target executable beneath the denied original home. The helper matched UID/path; no vendor code, task port or process memory was involved. A separate native compile/own-PID test plus synthetic compiler, file/hash, guard and dispatch regressions bring the suite to 75 passing tests. These checks do not establish vendor reader compatibility. A residual target-change race remains after identity inspection.

Fresh unsigned copy07 has patched ASAR SHA-256 `d6dbc279a13367ce7bba7aad64ce634efe2231a8ece25b90b8bb9127064dcdd4`. Its original-entitlement outer-only signing proposal is prepared; signing and launch await exact-copy approval. The helper is built separately per targeted profile; startup-only probes do not compile it. No policy, game bytes or entitlements changed.

Copy07 archive comparison confirms exactly the intended three packed entries differ and all three pass Node syntax checks. The other 138 regular files and all symlinks match the pristine source, including native code, signatures and Info.plist. The source ASAR still matches its pin. The read-only source image was detached after verification.

## Approved copy07 signing and transfer

The owner approved copy07 outer-only signing and the protected 45-second retry. Signing succeeded and deep strict verification, both original entitlement sets, Hardened Runtime and fixed nested/archive pins passed. Signed executable SHA-256: `6bfc801a5aece768b08c643c88759405b08ab8e4663a3e7b53841d09cb6ecb78`. The app/manifest/receipt-only 333-entry transfer archive matches the signed source byte-for-byte for files and symlink targets; SHA-256 `685c5c967bd5ab7a857a2eaa8ed525bc96ebbe9b52043b56afd3a6bf19efac36`. Original helper sources and observer/startup scripts were refreshed and syntax-checked. No profile, Terms, logs or credentials were transferred. No companion/game launch was executed during staging; reader/reward/overlay remain awaiting the owner-run observation.

## Copy07 native failure and controlled task-port matrix

The owner's latest reward observation passed the new identity guard, detected the exact game and recorded attach-attempt. Core logged `ScryRuntime.connect` followed by `Failed to connect to process` and `connect: false`. No connection acknowledgement or state/reward snapshot followed. The card photo shows Haze, Ricochet and Infinite Blades; those names are visual evidence only, not reader output or a verified reward comparison. OS log queries in the attachment-time interval produced no matching denial record. The native reader imports `task_for_pid` and memory-read functions; the game's original ad-hoc Hardened Runtime entitlements lack get-task-allow.

Ranked hypotheses before testing: target entitlement blocks task-port acquisition; outer confinement blocks it even for an entitled target; or the vendor reader/build has a separate failure. The original-fixture experiment tests the first two at the task-port boundary without executing vendor code. Apple documents [debugger/get-task-allow interaction](https://developer.apple.com/documentation/bundleresources/entitlements/com.apple.security.cs.debugger).

Native command, executed twice on this Mac in UID501: `python3 -m harness.attachment_diagnostic --run-original-fixtures`. Both runs completed with `TARGET_ENTITLEMENT_DISTINGUISHES_FIXTURES` and `targets_stopped: true`. The second run uses identical target signing identifiers and rechecks process start metadata/returned port PID. Results:

| Target get-task-allow | Outside outer policy | Inside unchanged outer policy |
| --- | --- | --- |
| Absent | denied, kernel return5 | denied, kernel return5 |
| True | acquired, kernel return0 | acquired, kernel return0 |

No target memory was read/written; only acquired task ports were deallocated. No game/companion files or global protections changed and no prompt was accepted. The second private report is `/private/tmp/untapped-attachment-diagnostic-0qe0grje/report.json`; exact policy SHA-256 `c2c44a105ae5c8c698c27ec98b5b76cd522fde8c03a99e4a2762c17103661e84` includes run-specific paths. The native fixtures/report remain outside Git.

This is evidence of an entitlement distinction for original test processes, not proof of the actual reader's failure cause. UID502 authorization context, the game's own sandbox, real memory reads/traversal and overlay are not reproduced. The staged test-account script repeats the same comparison without gameplay; any game-copy entitlement/signing change still needs a separate concrete proposal and approval. Seven portable regression tests cover classification, incomplete/invalid matrices, original-only commands, signature settings, dispatch, identity failures and multi-target cleanup. All 82 tests pass; native fixture execution is manual and not run in CI.

## UID502 fixture confirmation and unsigned game proposal

The owner's standard-account export confirms all four original-fixture cells in UID502: absent get-task-allow denied kernel5 inside/outside policy, present get-task-allow acquired kernel0 in both. It records no memory read/write, no game/companion modification and all fixture targets stopped. Fixture hashes match the second UID501 run exactly. The policy hash is `c70a36750c279143500a23c989f8ec7b550a3e5d8aa52476ea4692eebe63a566`; policy text differs only in account/session paths. This supports a game entitlement experiment, not a proven real-reader diagnosis.

Copy-only preparation succeeded at `/private/tmp/untapped-sts2-debug-game-01/SlayTheSpire2.app`. The installed source and copied tree match all 440 recorded entries, full tree hash `4892eb6c03ae851fde4f075c5ca75d9db827b84b2c651bcc9b5e62cd41add85e`. Both original architectures' four entitlements, ad-hoc Hardened Runtime, pinned assembly/version and deep strict signature verified. `/private/tmp/untapped-sts2-debug-game-01-proposal.json` contains the exact pending outer-only signing command and five-entitlement plist (original four plus get-task-allow). No game signature has changed.

The real `sign` command without its approval flag returned exit2 before any mutation, left the executable hash unchanged and created no receipt. Nine new synthetic game-debug tests plus four launcher/reader dispatch tests bring the suite to95 passing cases. They cover complete source pinning, copy-only proposal, approval refusal, allowed signing scope, receipt/file/mode/entry tampering, exact installed identity/path and no-spawn failures. Codesign mutation is mocked in tests; no vendor code executes. Shell, embedded Python, bootstrap syntax and repository hygiene checks pass.

Actual proposed signing, post-signature payload verification, profile-free archive transfer, test-account installation and bounded game/reader runs remain pending explicit approval. New scripts/helper versions are prepared in Git only; current live transfer and existing isolated game are intact. No normal-account save or Steam configuration change occurred.

## Approved debug-game signing and transfer

The owner approved the exact prepared outer-game signing plus the60-second boot check, up to900-second manual play and protected45-second reader test. Signing and subsequent independent `game_debug verify` succeeded: both architectures' deep signature, ad-hoc Hardened Runtime, original four entitlements plus get-task-allow, immutable source pin and full receipt/tree agreement passed. Exactly `Contents/MacOS/Slay the Spire 2` and `Contents/_CodeSignature/CodeResources` changed; all file modes and other entries match baseline. Signed executable SHA-256 `74ba017ccac7626b9f269f8d2bf31dc2d185c64442bb18d5fa9a2abe910c6b63`. The installed source remains unchanged.

The443-entry signed transfer contains only the app, baseline and signing receipt. All archived file bytes/modes and symlink targets match the verified signed source. Archive SHA-256 `288503d9974b4e9d8c5c7917851187cf33bec3a46a17d1bca7c6d619fca1e8e4`; checksum validation passed. Original helper sources plus install/play/observer scripts match repository bytes and pass shell/embedded-Python syntax checks. No profile, saves, Terms or credentials were transferred. No game/companion launch occurred during staging. Prior95 behavior tests remain applicable; only evidence documentation changed. Test-account install/boot, reader attachment/state/reward and overlay remain pending.

## Debug-game transfer permission mismatch and extraction fix

The owner-run installation passed archive checksum validation, then failed source receipt comparison before creating the destination session. The installer used umask077 and tar -xf, which masked archived permission bits. An inert real-archive test reproduced recorded0755 becoming0700. Repeating that exact extraction invocation against the unchanged signed game archive in a disposable UID501 directory reproduced427 changed entries: every content hash matched and no entry was added; only file modes differed. This reproduces the photographed failure without accessing the owner's private UID502 extraction.

`game_debug.extract_transfer` now requires an empty owned0700 canonical private destination and uses bounded tar -xpf, preserving archived file modes. The installer still checks archive checksum first and performs the full existing signature/entitlement/baseline/receipt checks afterward. No receipt normalization, permission relaxation, signed-byte change or re-signing was performed. The outer extraction root remains0700. The old failed test-account extraction is preserved and retry creates a new one; the destination-new guard remains in place.

Regression command `python3 -m unittest discover -s tests -p test_debug_transfer.py -q` first failed the exact mode comparison with0755 versus0700, then passed after the fix. Its three tests cover private-umask byte/mode preservation, refusing nonempty/redirected destinations before tar, and extraction failure. The full98 tests pass. Fixed real-archive extraction under the same umask matched all440 signed entries and passed deep signature and both-architecture settings/receipt verification. Original helper and installer bytes/syntax are verified in the staged transfer. Actual UID502 installation and game boot remain pending retry; the original signing/gameplay approval remains valid.

## First real native reward state

Following successful standard-account installation, the owner confirmed the debug-enabled game menu during the bounded boot test. The subsequent approved manual-play/protected45-second companion observation exported the complete ordered sequence bootstrap → ready → window-detected → attach-attempt → reader-connected → reward. No new launch or security change was performed while reviewing this evidence.

Independent transcription of the photographed titles and visible upgrade status matches captured HAZE0, RICOCHET0 and INFINITE_BLADES0 in left-to-right order. The captured centers are (0.3177083333,0.5703703704), (0.5,0.5703703704), and (0.6822916667,0.5703703704); each raw width/height is0.15625/0.3907407407. These are recorded values, not independent expected geometry. No compare-reward pass was manufactured from those values. Private captures/photos/logs remain outside Git.

Pinned-source tracing identifies the coordinate contract: ScryRuntime getCanvasItemData normalizes control global position and raw hitbox size by run.GlobalUi.getSize(), returning scaleX/scaleY separately. The existing overlay centers the raw box, then ScaledCanvasItem applies CSS scale. Our current bootstrap capture drops both scale fields. Consequently raw width/height cannot certify displayed bounds, and painted artwork can differ from the hitbox. The cropped phone photo lacks the complete GlobalUi viewport reference. Future independent geometry verification requires retained scales and a complete digital game-content viewport, with any border/letterbox offsets accounted for. Current compare-reward validates only its supplied raw geometry fields; it does not close this missing-scale gap.

The owner initially selected “overlay appeared” but clarified on follow-up that no overlay was noticed on the game screen; the corrected report governs this record. Static NGameStateOverlays wraps reward-overlay components in RequireLogin with showLoginNotice:false, and RequireLogin returns nothing without an account. The fresh offline profile has no account. Logs also report public game-data downloads blocked with no cache, and a CloudSaveStore/settings watcher “No such property” error. These explain concrete limits and are consistent with absent reward UI; they do not prove a native overlay-window rendering defect or broad game-version compatibility. No login gate is bypassed and no network allowance is added.

The native path is therefore demonstrated for this reward's IDs/upgrades after the explicit debug-game entitlement change. Full scaled geometry, vendor overlay display/alignment, ratings/advice, run tracking and untouched installed-game attachment remain unverified. Next work is a scale-complete capture proposal and separately reviewed isolated account/public-data plan if full Untapped UI is to be exercised. The existing98 portable tests remain applicable to unchanged code; no new test or redundant suite run is warranted for this evidence-only update.

## Prepared controlled sign-in and scale-complete copy08

Read-only auth/data tracing identified genuine OAuth PKCE/state with a loopback callback, global token/account and STS2 exchange/account/features routes. It also identified unrelated post-auth MTGA upload-token bootstrap, public-data versus gameplay-context POSTs, renderer artwork requests and unsafe raw authenticated logs. The implementation now preserves genuine sign-in while disabling that unrelated bootstrap and upload/metric producers, retaining app remote denial and routing reviewed Node-fetch calls through the default-deny original gateway. No vendor auth/feature gate is bypassed.

Copy08 is prepared unsigned/unlaunched with ASAR SHA-256 `1c343975300061b01917f5258d9f03089c0bb7ed9e21471e9560f055eeb02720`. Exactly three packed JS entries differ, all Node syntax checks pass, and the other138 regular files/all symlinks match pristine source. Native/framework/Info.plist and original entitlements are unchanged; the read-only image was detached. Exact signing and access proposals are outside Git. No copy08 signing, vendor app launch, real OAuth/account/public-data request, browser opening or credential access occurred during preparation.

All126 tests pass, including eleven local fake-upstream gateway tests, three adapter tests, two controlled auth/upload/metric tests, eleven supervision/export tests and scale-aware bootstrap/comparison cases. Local fake gateway probes reject unreviewed routes/methods/bodies, credentials/redirect misuse and excess resources; 304 caching remains supported. An inert sandboxed client reached only a fake local upstream under the unchanged outer policy, with public authorization stripped. These tests are not vendor integration evidence.

The capture now retains scaleX/scaleY and supports explicit rendered-hitbox comparison with required scale evidence; legacy raw comparisons are labeled incomplete. Shared authenticated diagnostics exclude raw logs/URLs/bodies/headers/account fields and include only whitelisted events/cards/status/counts and fixed settings/cache booleans. The full details, exact permitted disclosures and pending execution protocol are in [Controlled-Access-Plan.md](Controlled-Access-Plan.md). Settings-reader compatibility, live auth/data population, independent geometry, overlay display/alignment and ratings remain unverified.

Independent review identified and corrected three boundary issues before live execution: in-flight gateway handlers now drain before counters/export; prepared metadata pins the exact gateway/adapter bytes and rejects policy drift; the controlled supervisor preserves a nonzero/signal exit observed by poll after authentication. Regressions cover all three. The final126-test suite and loopback-only fake-upstream proof remain separate from vendor integration. Copy08's unsigned metadata/access proposal were refreshed with final original helper hashes; its ASAR and native payloads were not changed by those original Python/helper fixes.

## Approved copy08 signing and transfer

The owner approved copy08 outer-only ad-hoc signing and the first controlled manual sign-in probe (maximum300 seconds, at most45 after genuine authentication). Signing succeeded with original five entitlements on both architectures, ad-hoc identity and Hardened Runtime. Deep strict verification and native/framework/ASAR pins pass. Signed executable SHA-256: `5cc4476cf26ea005a0d4d69021dc9b70a6c7cf939fe9a7e348eb402aed8f3383`.

Staged companion08.tar SHA-256: `d8b847b8291c6a9f2da72246eabd810c3a52f2e8467681e5ff0c38b0212a85db`. All333 entries match source type/mode/content or symlink target; a private tar -xpf extraction reproduced the app tree and passed signature/payload/helper-policy verification. Compared with signed copy07, all file/symlink differences are confined to the new ASAR, outer executable signature and CodeResources; copy08 additionally retains55 empty locale directories absent from copy07. No profile/Terms/account/log data is archived. All17 original harness source files and the controlled launcher are staged with byte parity.

No executable behavior changed in this signing/staging slice, so the existing126 tests remain the applicable test evidence without redundant reruns. Shell syntax and repository/documentation hygiene are checked separately. No copy08 vendor process or live account/public-data request was started; live behavior awaits the manual owner-run login-only probe in UID502. Overlay/settings/independent geometry remain unverified.

## First controlled OAuth attempt: upstream token HTTP403

The owner ran the approved login-only copy08 probe in UID502. Sanitized /private/tmp/sts2test-controlled.7a7o1dnx.json contains bootstrap at20:15:07Z, ready at20:15:08Z and manual-sign-in-ready at20:15:30Z on2026-11-03, Core initialized, no startup blockers, exit0 and complete gateway cleanup. Exactly one oauth_token request received403, with no denied-route count and no authenticated/account/public-data event. The owner photographed browser and companion authentication errors. The counter is recorded after request validation and upstream transport, so this was not a local allowlist rejection; its actual upstream cause remains unknown.

Read-only replay of the sanitized result confirms those assertions. Local inert validation also accepts the pinned vendor's authorization-code form shape at api.accounts.untapped.gg/o/token. Neither observation proves that the live authorization code, PKCE exchange, upstream headers or response body was valid. The login-only false settings/cache flags do not overturn the separate game-settings limitation.

Added an original owner-run saved-error classifier, with seven synthetic tests covering fixed HTML/security/OAuth categories, ignored unrelated text, secret exclusion, input bounds, controlled metadata, ownership/link/path checks, preserved source bytes and generic failures. It reads private logs only inside UID502 and exports safe fixed fields without executing the vendor or making a request. The first actual saved-error classification is pending owner execution; no transport/security bypass or gateway-policy change is made on speculation.

All133 tests pass. The original classifier/wrapper are staged with byte parity; shell syntax, staged help/import, existing gateway/adapter policy pins and documentation/repository hygiene pass. Copy08's signed payload and approved gateway/adapter bytes are unchanged. Only the owner-run read-only classifier remains for this diagnostic step.

## Original-client header correction and revision08b

The owner-run saved-error export sts2test-auth-error.sab2rzl0.json is UNCLASSIFIED_TOKEN_ERROR: token/callback failure logged, no exchange completion, no HTML/challenge/provider/known OAuth markers, both files read without truncation. This limits the saved evidence; no raw log/body/account material was exported.

Read-only inspection of the pinned node_modules/node-fetch/lib/index.js reproduces its default User-Agent: node-fetch/1.0 (+https://github.com/bitinn/node-fetch). Our urllib gateway had omitted it and used Python's default, as described in the [stdlib Request documentation](https://docs.python.org/3/library/urllib.request.html#urllib.request.Request). Two HTTPS GETs to the existing reviewed api.accounts.untapped.gg/api/v1/account endpoint, changing only User-Agent, returned403 text/plain17 bytes with the default and401 application/json85 bytes with the original-client value; the latter had the fixed missing-credentials message. No credentials, cookies, request body/query, redirects or browser/app execution were involved. Safe fixed metadata is retained at /private/tmp/sts2-auth-transport-comparison-01.json. This demonstrates header-dependent transport behavior, not successful OAuth or a proven internal reason for the upstream filter.

New tests/test_gateway_client.py exercises real urllib HTTP output against an original inert loopback server. The exact regression failed403 versus expected401 before the fix and passed afterward. The transport now sets only the fixed original User-Agent; caller-supplied User-Agent remains rejected. Existing gateway and controlled tests additionally verify that denial, proposal disclosure and the new path-only cat instruction without gateway-secret disclosure. All134 tests pass using synthetic/local test traffic; the two diagnostic vendor GETs above are separate finite runtime evidence.

Revision08b at /private/tmp/untapped-native-sts2-poc-08b has an app tree and signing receipt identical to signed copy08, including file bytes/modes/symlink targets. No new signing or ASAR/native/entitlement change occurred. Deep signature/payload verification passes. Fresh metadata pins gateway SHA-25670d78c4798db97790fead4e22a41e061c241f2f3373f18aac6d5f46ff9c3cdd3; the adapter is unchanged. The review proposal includes the fixed User-Agent, previous hash, unchanged-app/signing/route scope and no new live OAuth attempt.

The333-entry companion08b.tar SHA-256 is8d1587fb765e9f008258b72bd2c8fea3ff44b3cf8747c4d41963165f3097939a. Every entry and a private exact-mode extraction match, and extracted signature/payload/policy checks pass. Only app/manifest/receipt are archived. Old archives/metadata are preserved; current helpers deliberately reject their stale controlled gateway hash. The revised default launcher selects08b and requires the owner to initiate the next bounded manual login-only attempt. No revised live sign-in is performed during preparation; authentication, game-settings compatibility and visible overlay remain unverified.

## Revision08b owner-run exception502 and fixed-data transport diagnosis

The owner ran08b and exported /private/tmp/sts2test-controlled.w7jrcoj3.json. It records bootstrap20:47:21Z, ready20:47:22Z and manual-sign-in-ready20:47:38Z on2026-11-03, Core initialized, no startup blockers, exit0 and complete gateway cleanup. No authenticated event occurred; only the generic gateway error502 counter occurred once. This is an exception branch rather than an upstream status; its cause cannot be inferred from that counter. The owner saw the browser/companion authentication-error dialog again.

One separate fixed nonexistent-client/code/verifier POST from UID501 to the reviewed token endpoint returned401 JSON invalid_client under the current transport. No real account or OAuth code was used. The exact launcher interpreter is Python3.11.2; UID501 has a readable default CA file and no SSL_CERT_FILE/SSL_CERT_DIR overrides. This does not reproduce UID502's failure. A read-only independent audit exercised original inert HTTP and local-test-certificate TLS servers with200 keepalive, connection close, chunked and401 responses; those cases completed without a transport exception. No repository edits or vendor requests were made by that audit; production TLS/trust was not changed.

Added harness/transport_diagnostic.py and a standard-account wrapper to identify same-user TLS/DNS/timeout/connection/response/interface failures with fixed categories. Its only possible requests are the existing account GET without credentials and token POST with fixed nonexistent data, stopping at the first transport exception. No logs, saved request, user URL, real client/token/code, browser or app is used. Shared sts2test-transport.*.json exports fixed status/type/byte counts, bounded numeric errors and runtime/CA booleans; no raw exceptions/responses or environment/path values. Five new synthetic tests cover all categories, scope, fail-fast behavior, export privacy and account guarding. UID502's actual result remains pending; gateway/adapter policy pins and signed payloads are unchanged.

All139 tests pass. The checker/wrapper are staged with byte parity; shell syntax, staged help/import, existing08b policy-hash verification, documentation links, repository hygiene and whitespace pass. The checker was not run against vendor endpoints in UID502 by the assistant; its owner-run result remains pending. Source account files/logs and all signing/app/gateway/adapter/manifest bytes were preserved.

## Revision08c preflight and private failure evidence

The owner-run /private/tmp/sts2test-transport.lawr_85r.json records both fixed-data routes completing with401 JSON (85/27 bytes), Python3.11.2, accessible default CA file and no CA overrides. It did not reproduce08b's real-flow error502. A separate UID501 capability-gateway comparison using the same fixed inputs also returned401 upstream/locally with no failures and clean drain; safe metadata is /private/tmp/sts2-gateway-transport-comparison-01.json. Neither check proves real authentication or identifies its exception.

Revision08c validates the signed copy before a two-request preflight through the actual gateway. Both expected401 responses must be bounded strict UTF-8 JSON objects; malformed/empty/scalar/nonfinite/duplicate-key responses fail. Failure or exhausted budget opens no app; validation/preflight time reduces the existing300-second app window, preserving45 seconds after genuine auth. Generic gateway failures retain fixed route/stage/category, bounded timing and optional numeric codes, capped32 with overflow count. Safe exports separate preflight/app counters and correctly attribute late no-app failures after drain. No raw exception/URL/header/body/account data is exported, and preflight does not substitute for authentication.

Eight new gateway and seven supervisor tests cover fixed request scope, malformed JSON, failure bounds/privacy/drain, signed-copy-before-network, no app on failure, remaining time, counter/phase separation and closed-stream response handling. All154 tests pass with inert/fake test traffic. Independent review found JSON-body trust and late-attribution defects; both are fixed and regression-covered, with additional strict nonfinite/duplicate rejection. A real UID50108c preflight then returned both401 JSON objects, no failures and clean drain; /private/tmp/sts2-gateway-preflight-08c.json contains only safe metadata. No app or real OAuth was used for it.

Revision08c's signed app tree and receipt are identical to08b/08, including bytes/modes/symlink targets. No signing/ASAR/native/entitlement change occurred. Gateway SHA-256 is79c16a7e9cacba58dfaa23b96b0446ddf9496101dd7da00a8e00c675898c85e5, CJS adapter unchanged. Fresh metadata/proposal records the preflight/error scope and previous hash; original manifests remain unchanged. The333-entry companion08c.tar SHA-256 is5453194a1674b54386524df00080eb2a4cab5b36ec12d5e0a6d3102d05e594bd. Every archive/extracted entry matches and native signature/payload/hash verification passes. Only app/manifest/receipt are transferred, with current original sources and default launcher staged by byte parity. No08c real login or companion run occurred; the owner-run result and actual failure cause remain pending.

## Verified controlled sign-in on08c

The owner reported successful sign-in. Sanitized /private/tmp/sts2test-controlled.mjy01eeq.json confirms bootstrap21:25:44.183Z, ready21:25:44.882Z, manual-sign-in-ready21:26:02.216Z and authenticated21:26:36.436Z on2026-11-03. Preflight passed both expected401 JSON objects; companion traffic separately records one oauth_token200 and one accounts_account200. Core initialized with no startup blockers, no gateway failures/overflow and complete cleanup after the configured45-second post-auth limit. No failing native exit is recorded. No raw log/account information was included.

This establishes the original PKCE/callback/token/account-verification path and genuine auth event under the controlled gateway. It does not identify the older502's cause or prove that preflight itself fixed it. No game, STS2 exchange/features/public JSON route or reward event was observed in this login-only run. False settings/cache flags here do not settle compatibility with a running game, and overlay/ratings/independent geometry remain unverified.

The next existing workflow is the approved900-second debug-game manual session followed by controlled_sign_in.sh --observe-debug-game at an unchanged reward screen. The same fresh-profile/memory-only design requires manual sign-in again. No signing, policy, app or test changes are needed for this evidence update; the existing154 tests remain applicable. Validate documentation/script syntax/hygiene and record the combined result separately.

## Authenticated08c reward result: no visible overlay

Sanitized /private/tmp/sts2test-controlled.rbnc3vt6.json records bootstrap21:42:47.258Z, ready21:42:47.971Z, window-detected21:43:06.764Z, attach-attempt21:43:06.893Z, reader-connected21:43:07.200Z, first reward21:43:07.669Z, manual-sign-in-ready21:43:10.607Z and genuine authentication21:43:37.467Z on2026-11-03. The42 reward events span authentication; all three IDs/upgrades match HEADBUTT0, FORGOTTEN_RITUAL0 and INFERNAL_BLADE0 in the photographed order. This establishes actual native reward access during the authenticated controlled run.

The recorded normalized centers are0.3177083333333333,0.5,0.6822916666666666 at cy0.5703703703703704. Raw hitboxes are0.15625×0.3907407407407407 with baseline scaleX/Y0.800000011920929 and interaction changes up to1. These reader values are observed evidence, not independently transcribed expected geometry. The owner's photo crops the viewport and has perspective, so no independent complete rendered-geometry match is claimed.

Companion counters record accounts_account200×1, oauth_token200×1, sts2_exchange200×1, public_json200×6 and tier_resolve200×8. One denied403 request remains unidentified by design; it cannot be assigned to a route from this export. Preflight401s are separate. Core initialized, no startup blockers/gateway exceptions/overflow, complete cleanup and the intended post-auth cutoff are recorded. settings_property_error is true, public_data_cache_missing is false. Successful responses do not prove all parsing, entitlement gates or UI behavior. The owner explicitly reports **no overlay**.

## Copy09 native settings and normal Mac Tiers controls

Read-only static inspection of pinned game assembly SHA-256e7ceb80669bfaf5c8fccabaa126ae2bb283aba514be5b5b55612579cfd285f18 (v0.107.1, commit59260271) finds SaveManager.ConstructDefault MethodDef1825, RVA0x3ab20: GodotFileIo construction at IL0032, Steam-uninitialized branch to IL00a8, and CloudSaveStore wrapping at IL009e only on the initialized path. SaveManager constructor1824 stores its first ISaveStore parameter into _saveStore. Both class/property names exist; this is a type variant, not a demonstrated renamed member. No game assembly was loaded or executed for this inspection.

The original native wrappers expose full className and preserve the native handle through cast. The new helper selects exact MegaCrit.Sts2.Core.Saves.GodotFileIo directly, or exact MegaCrit.Sts2.Core.Saves.CloudSaveStore followed by a positively validated GodotFileIo inner LocalStore. Unknown outer/inner classes and native read/string errors fail. No default settings, save paths or substitute state are invented. Runtime recovery remains pending.

Source tracing also corrects the causal limit: missing settings can leave getTargetResolution null, but GameOverlay has a window-bounds fallback and public definitions have a latest fallback. Thus settings failure does not itself prove why the owner saw no overlay. Fresh badgeMode is stats under this intentionally public-only policy. The settings UI originally hides STS2 on packaged Darwin; the exact new edit adds only Darwin to its STS2 entry. Login/features, other games, packaged status and the owner-selected mode remain intact. The owner can now choose Slay The Spire 2 → Badges → Tiers; no creator/mode/score is forced.

Fixed settings-read, overlay-ready and overlay-show events contain only event/time. The new settings_reading and overlay_window report fields expose stages without changing overlay's UNTESTED_REQUIRES_VISUAL_CHECK result. Tests explicitly establish that renderer-ready or show-call markers cannot certify visibility.

Plan checkpoint343878d precedes implementation checkpointa39f689. Five new store tests and three UI tests plus archive cardinality/guard and lifecycle/privacy regressions bring the suite to164 passing tests. Native syntax checks pass for all five patched JS entries without executing vendor code. Independent read-only review found no concrete correctness/privacy issue. Full source comparison covers15099 ASAR entries: exactly Core, main entry, Services, ScryRuntime and Main settings UI change. All329 other app entries match type/mode/content/link target; the atomic private ASAR replacement has mode0600 instead of source0644.

Fresh copy09 preparation at /private/tmp/untapped-native-sts2-poc-09 has ASAR SHA-256adf595a36aac17382e928761c0120660b22e2604d75b6dd49ead054f213eddad. The established approved outer-only ad-hoc reseal retains the original five entitlements on both architectures and Hardened Runtime; only outer executable and CodeResources change during signing. Signed executable SHA-2568c094796bf03defd58392f416a6f9abd37cd4b36e153b5c6bad82bdc4fef8145. Deep strict native verification passes; no nested, game or OS-security change. The source image was detached.

Staged companion09.tar SHA-256c07adcadef591266773616252f74fb553436bd053a72021f21d9ac2ddaedf447 has333 entries, each checked for exact type/mode/content/link target. A private tar -xpf extraction reproduces signed bytes/modes and passes signature/payload/policy checks. Only app/manifest/signing receipt are transferred, with current original helpers and launcher matching repository bytes; older archives are preserved. Gateway hash79c16a7e9cacba58dfaa23b96b0446ddf9496101dd7da00a8e00c675898c85e5 and adapter hash91018dd8955e51a5f4edb9f517a3262d172d4e4b30c20f6eb664b6a137870c02 remain08c. No new route, native module or entitlement is added. No09 app, game or real OAuth request ran during preparation. The bounded owner-run settings/Tiers/visual test and independent geometry remain outstanding.


## Copy09 visible overlay and settings recovery

The owner supplied a photo showing badge placement under Collision Course, Astral Pulse and Celestial Might after choosing Tiers. Sanitized /private/tmp/sts2test-controlled.yzm82cgr.json records genuine authentication, exactly one reward event with COLLISION_COURSE0/ASTRAL_PULSE0/CELESTIAL_MIGHT0 in that order, settings-read, overlay-ready and overlay-show. The prior settings-property error is false and public-data-cache-missing is false. The reward uses the same normalized centers/raw hitboxes and0.8 scales observed previously. Core initialized with no startup blockers, account/token/STS2 exchange/account/features responses200, public_json200×12, tier_resolve200×8, no gateway exceptions and complete cleanup. Nine denied requests remain unidentified by the sanitized design; their identities are not inferred. No09 signing, runtime or network scope was added for this evidence review.

The photo establishes visible rendering and approximate association with the cards. It does not independently validate complete viewport geometry. Labels appear as ?-Tier: source formatTierLabel uses that fallback for absent/falsy tier data. Any enabled list can admit the badge UI, while merged card ratings are filtered to the current character plus Colorless. A successful HTTP200 tier request is not proof that the relevant cards have ratings. The preceding t6ewzvvg run recorded settings/renderer readiness but no reward/show before its cutoff; the owner had not reached the reward screen in time.

## Main-account existing-progress readiness milestone

The owner explicitly selected eventual use of existing normal macOS and Steam progress. That choice is recorded in the [migration plan](Main-Account-Migration.md); main-account execution remains inactive. A fixed-path read-only inspector verifies public vendor metadata/pins and bounded game-data directory metadata, excluding save/Steam-config/auth contents and private identifiers from output. Its synthetic tests exercise privacy, missing/redirected/inaccessible paths, owner checks, bounded inventories and no-launch/no-write behavior. Actual fixed-field result and test count are recorded below after validation.

Static PCK project configuration uses a custom user-data directory named SlayTheSpire2. UserDataPathProvider methods2125/2128/2130 derive steam/default namespaces, local-player IDs and normal/modded profileN directories. SaveManager wraps the local store with SteamRemoteSaveStore/CloudSaveStore only after Steam initialization. Static NGame startup performs migrations/cloud sync before profile initialization; bundled documentation says sync may overwrite local data. SteamInitializer method4084 calls InitEx; no direct managed restart-helper reference or steam_appid.txt was found, which does not prove external-copy Steam initialization or absence of native relaunch paths. No assembly/vendor code, save data, Steam config or Cloud metadata was executed/opened for this source inspection.

Readiness execution result: `python3 -B -m harness.main_account inspect` completed in the normal account. Public vendor release/assembly match the pins; the fixed game-data root contains one Steam user namespace with one normal profile and no modded profiles. A local/default namespace contains one user directory and no profiles observed. Inventories are complete within the bounded scan; paths/names/Steam IDs/save fingerprints are absent from output. Cloud remains UNVERIFIED and main launch remains false. All reported activity flags for save contents/network/writes/signing/persistent credentials are false. No save validity or currently logged-in Steam identity is inferred. The helper itself writes no report file; only fixed JSON was printed.

Eleven focused inspector tests pass. The full suite and final hygiene are recorded in the implementation plan after the final check. Independent review found no additional blocking issue after no-follow descriptor walking and nonblocking FIFO rejection; reaching an exact scan cap intentionally remains conservative/unverified. Only the new helper/tests and documentation change; existing isolated execution guards, native signatures, companion gateway/adapter and staged09 launch bytes are unchanged.

Final readiness validation: all175 tests pass, including11 new synthetic inspector tests. Original helper/bootstrap syntax, controlled shell syntax, repository/Markdown/whitespace checks pass. Plan checkpoint01452cd precedes the code and final documentation checkpoint. No native runtime, signing, account credential, save or Cloud mutation occurred in this milestone.


## Implemented main-account launcher, unsigned activation pending

Plan checkpointbac00d4 and implementation checkpointd2ee81f record the new separate main launcher. All218 tests pass, including43 new synthetic cases for backup integrity/races/links/bounds, expected Steam/profile guards, positive overlay display gating, preference filtering and descriptor swaps, long supervision, helper cleanup, failure diagnostics and action ordering. Independent review findings were addressed with regressions: null/mismatch context cannot display the overlay, already visible UI hides in finally on mismatch, exited leaders still trigger group cleanup, interrupted cleanup is not reported complete, source/copy validation repeats after opening Steam, and private profile I/O holds no-follow directory descriptors. Fixed-stage failures now retain private evidence and still produce a safe diagnostic after gateway drain.

The prepared main workspace contains an unchanged unsigned game copy (all440 entries equal to the installed pinned original, tree4892eb6c03ae851fde4f075c5ca75d9db827b84b2c651bcc9b5e62cd41add85e) and an unsigned companion with ASAR2daf620993d64105d37d45ce2ad3fca38bdd3ba9d13d12614438bf7408af455c. All15099 archive entries were compared: exactly five packed JavaScript entries change and syntax-check. All329 other app entries, native binaries, original executable and Info.plist are unchanged; the private atomic ASAR resource replacement uses mode0600. Private Steam/profile binding is absent from the shareable proposal. No game/companion signing receipt or activation receipt exists; backups/runs/preferences remain empty. The source image was detached after verification.

The exact review document is local at the dedicated main workspace's main-proposal.json. It proposes outer-only ad-hoc game signing with original four entitlements plus get-task-allow, and outer-only companion signing with the original five entitlements; Hardened Runtime and nested code stay. The runtime plan creates a stable verified local progress backup before Steam startup, rechecks source/progress, runs the copied game with genuine Steam AppID2868840/force-steam=on/nomods and normal user/Steam permissions, and confines the companion to the existing gateway/outer policy. Account/profile is a positive native overlay gate, not an inference from Steam initialization logs. Main companion defaults to4 hours without post-auth shortening, with8-hour maximum; no game is killed or restored automatically. Preference carry excludes auth/account/Chromium data, and fresh main Terms acceptance remains manual.

Gateway79c16a7e9cacba58dfaa23b96b0446ddf9496101dd7da00a8e00c675898c85e5 and adapter91018dd8955e51a5f4edb9f517a3262d172d4e4b30c20f6eb664b6a137870c02 are unchanged. No real progress contents were opened, no real backup was taken and no native app, sign-in, remote request or additional signing ran during implementation/preparation. Actual main-account Steam initialization, Cloud/profile behavior, normal save/exit, real tiers, fullscreen and broader overlay coverage remain live checks after explicit activation approval. Existing isolated guards/launch bytes are preserved. Shell/JS syntax, Python compilation, repository/Markdown/whitespace checks pass.


## Approved main-account copied-app activation

The owner approved the exact prepared game get-task-allow signing, copied-companion reseal and first backed-up main-account Steam-progress scope. Plan checkpoint0886ff1 records that approval. `scripts/main_account.sh activate --approve-main-copy-signing` completed successfully with copied_apps_signed true, game_launched false and progress_written false. No additional approval was requested.

Post-operation validation passed the full440-entry signed-game receipt, source-tree pin, both apps' deep strict signatures, both architecture entitlements and ad-hoc/Hardened Runtime flags. Only game executable/CodeResources changed under signing; installed source tree4892eb6c03ae851fde4f075c5ca75d9db827b84b2c651bcc9b5e62cd41add85e is unchanged. Signed game executable74ba017ccac7626b9f269f8d2bf31dc2d185c64442bb18d5fa9a2abe910c6b63. Companion ASAR2daf620993d64105d37d45ce2ad3fca38bdd3ba9d13d12614438bf7408af455c is unchanged from preparation; signed executabled851fe580ba09359ff9998f9d3f894d25f404fa9e995807ec4e25f4b428f0ddd. Full companion comparison with signed09 finds only the new ASAR, outer executable and CodeResources differ; all entry names/types/modes and remaining resources/payloads match. The activation receipt's proposal hash matches the immutable owner-reviewed proposal.

The native verification record is private in the main workspace as activation-verification.json. Backups/runs/preferences are still empty; real progress contents, Steam configuration, account/auth data and Cloud metadata were not opened. No game/companion, backup, sign-in or remote request ran. The first live launch is owner-initiated through the interactive Terminal sequence after Cloud/account confirmations. These remain factual prerequisites rather than duplicate approval. No executable source/test change occurred in this signing/evidence slice, so the existing218 passing tests remain applicable without a redundant rerun; native checks and documentation/syntax/hygiene checks provide the new evidence.

## Main-account UI assets and character defaults — November 10, 2026

The owner confirmed actual tier ratings on a main-account reward screen after fixed events recorded authentication, expected Steam/profile match, reader connection, reward detection and overlay-show. The subsequent screenshots exposed blocked static images and FontAwesome checkmarks; source inspection confirmed the commentary background also depended on a remote image with no opaque fallback.

The installed separate `companion-ui` embeds30 public assets into four renderer entries. Its ASAR is `f6c5a7d747c564608ed552dcc3ae8881407fdf563196e7a3de078577953306a1`, derived from retained base `2daf620993d64105d37d45ce2ad3fca38bdd3ba9d13d12614438bf7408af455c`. All other ASAR entries/native resources remain equal. Full copied app comparison permits only ASAR, outer executable and resource seal differences; deep strict signature and both original five-entitlement sets pass. Runtime gateway/adapter hashes remain fixed. No game/session was started or stopped and no save operation was performed during installation. A staged archive permission mismatch was caught before activation, repaired with mode preservation, and regression-tested.

An offline headless Chrome fixture rendered the actual embedded five character images, visible checkbox tick and commentary backgrounds against patterned card placeholders, including the opaque fallback with the decorative image disabled. Screenshot: `/private/tmp/untapped-ui-render-check/preview.png` (private local artifact, no account/gameplay data). This is a component rendering check, not a live reward-screen observation of the updated build. All four final renderer entries pass Node syntax checks. The ten pinned default tier UUIDs match the bundled source; synthetic persistence coverage verifies all five colors, author preference, custom-list preservation and one-time migration respecting later manual disabling.

The existing session continues using its earlier copy. Live updated companion rendering and all-character metadata refresh require the next normal launcher run; post-game Steam Cloud synchronization and full-run stability remain unverified.

Final automated validation: all231 tests pass (13 new cases across asset preparation, update selection and character-list persistence). Node syntax, repository hygiene/Markdown links and whitespace checks pass. Independent review found CSS import ordering and font-request bounds issues; both were corrected before installation. Third-party assets, private profiles and preparation artifacts are excluded from Git.

## Pending tier metadata settings crash — November 10, 2026

After signing into the UI update, the owner reported a blank STS2 settings page. A bounded local log classifier found only the sanitized signature `TypeError: Cannot read properties of undefined (reading 'localeCompare')`; the current index had11 entries, three missing names. The native `TierListSettings` sorts the entire index immediately, while `verifyIndexIntegrity` starts metadata refreshes without awaiting them. Our minimal seeded selections lacked the name expected by the comparator.

A Node replay using the exact bundled `DEFAULT_AUTHORS`, `isDefaultAuthor` and `sortTierLists` fails with the same exception on synthetic pre-fix entries (exit1) and succeeds on repaired seed output (exit0). Fresh profile entries now include the truthful temporary name `Loading tier list…`. No author/ratings are invented; missing keyCards/gameVersion still trigger native metadata refresh, and preference harvest strips the temporary name. Persisted preferences remain UUID/color/enabled only, plus the migration marker. This fixes both imported saved selections and all-character defaults before the first render; no signed ASAR or permissions change is required.

Regression coverage first failed on the missing name, then passed after the seed fix, including sorting and harvest privacy. The original fixture-only visual check missed this asynchronous application-state race; it did not exercise the settings page's native tier comparator.

All232 tests pass after the regression fix. The unchanged signed UI copy was validated and reopened under the existing supervisor beside the same verified running game; only the previous companion process group was terminated. New-profile tier entries all have string names, and startup reaches ready. The owner must manually sign in and confirm the settings page; there was no automated login, game restart or save operation. Repository/Markdown and whitespace checks pass.

The owner subsequently signed into the reopened companion and confirmed that clicking Slay the Spire 2 displays the settings page. This closes the reported blank-page regression with live visual confirmation as well as the native comparator replay. It does not establish every pending tier list's metadata availability or a complete game/Cloud test.

## Tier-list queue and bounded retries

The live loading-label diagnosis found six tier-resolution connection resets. A synthetic local reproduction filled the gateway's eight handlers; the ninth request was closed without reaching the fake upstream. This establishes a local burst failure rather than an account/permission failure for those six downloads.

The repair queues companion requests at four concurrent body-complete operations and retries only transient public tier-resolve GET failures. An integration replay used the actual signed bundle's node-fetch2.3.0 with the real Python gateway and an injected fake upstream: all18 startup responses completed, maximum upstream concurrency was4, and all12 tier reads recovered from one simulated503 each (30 total upstream fixture calls). The vendor Response type, JSON/clone/bodyUsed semantics, ETag preservation and public credential stripping passed. No real remote request or account data was used. Synthetic adapter regression and full-suite results are recorded below after validation. Live all-character metadata completion remains a separate check after owner sign-in.

Validation: all237 full-suite tests pass, including eight focused adapter tests for shared FIFO/body-complete scheduling, queue overflow and expiry, transport/status retry exhaustion,401/403/404 and OAuth single-attempt behavior, and request/response size limits. Node syntax, diff whitespace and repository checks pass. The explicit main-account adapter migration completed with SHA-256 `9bc46aee98373ada76fe17c5e6f3e79ef4ae09cc79bd02cc0630201446554850`; both installed manifests now pin it. The original gateway SHA-256 `79c16a7e9cacba58dfaa23b96b0446ddf9496101dd7da00a8e00c675898c85e5`, immutable approval hash and both signed payloads verify unchanged. Private original-manifest/update receipts remain in the main workspace.

Live rollout: the companion-only supervisor verified the exact existing game and signed companion process group, stopped only that companion group, then opened a fresh companion using the new pinned helper. The running helper hash matches the tested repository adapter. All12 genuine metadata entries (two per Ironclad, Silent, Regent, Necrobinder, Defect and Colorless) now have names, keyCards and gameVersion, with zero pending or enabled-pending entries. All12 matching cache files exist with nonempty item collections (64–314 entries). This verifies real tier download completion and closes the persistent-loading report. Owner sign-in for the fresh session and any subsequent overlay visual check remain separate; the game was retained and no save/Cloud operation was performed by this repair.

After the owner reported sign-in, a bounded fixed-field check confirmed authenticated, main-steam-verified, reader-connected and overlay-ready events. All12 lists remained loaded with zero pending entries. No account identifiers, tokens or raw log text were exported.

## PR review: safety-stop exit status

The sampled Brooks review found that a previously authenticated and verified main session could return CLI success after its process-identity guard stopped the companion with `TARGET_CONFLICT`. The CLI now also requires a known normal stop reason: game exit, companion exit or session limit. Synthetic regressions reject target conflict, account mismatch and unknown/missing reasons while preserving the normal outcomes. They failed before the fix and pass afterward. All238 tests pass locally with localhost fixture-server access; the restricted sandbox initially denied those servers. Repository, whitespace and JavaScript checks pass. No real app, save or Cloud operation was performed.

The first PR CI run failed on Ubuntu with platform-dependent test fixtures; investigation is tracked separately from this exit-status correction.

## PR CI fixture portability

Ubuntu CI initially reported7 failures and17 errors: the game fixture's hardcoded UID501 disagreed with real temporary-directory ownership, Darwin errno61 did not mean connection refused on Linux, and the fixed macOS `/private/tmp` namespace was absent. The fixtures now use the actual test UID and `errno.ECONNREFUSED`; the ephemeral CI runner explicitly provisions `/private/tmp` with mode1777. Production validation, private0700 fixture directories, namespace assertions and test coverage remain unchanged. No production code changed for this CI correction. All238 local tests and repository/whitespace checks pass; the next Ubuntu run verifies these fixes on the original failing platform.

## Codex PR review: companion crash classification

Codex reported two actionable findings: Ubuntu fixture portability (already corrected in cb7e29b and verified by passing CI), and a nonzero/signal companion exit incorrectly treated as a normal quit after authentication. The supervisor now distinguishes `COMPANION_CRASHED`; run diagnostics preserve the pre-cleanup exit code and mark `PROCESS_EXIT` failure while retaining private evidence. Cleanup still reaps the owned companion group, and the launcher returns nonzero. A still-running process stopped by the supervisor is not misclassified as a spontaneous crash. Synthetic tests cover normal0, failure1 and signal-11 outcomes and launcher rejection. The regression failed before implementation; all239 local tests, repository checks and whitespace checks now pass. A focused independent review found no further actionable issues. No live companion/game or progress operation ran.

## Follow-up Codex review: game crash classification

Marking PR2 ready triggered an additional Codex review of71afd93. It found that a copied-game crash could still look like normal game exit. The launcher now records `game_exit_code`, classifies a disappeared target with nonzero/signal status as `GAME_CRASHED`, and treats disappearance without a confirmed exit as `TARGET_CONFLICT`. Companion supervision accepts the crash reason, retains private evidence and completes owned-group cleanup. The CLI also rejects a nonzero game exit first observed after a normal companion stop. No game termination or save restore was introduced.

Synthetic regressions failed before implementation and now cover exit0, exit1, signal-11, unknown status, retained evidence, and late crash reporting. All242 local tests pass, including53 focused main-account cases; repository/Markdown and whitespace checks pass. No live app, game, save or Cloud operation ran.

## Attack-summary icon repair — November 10, 2026

The owner reported a broken image in the enemy attack summary during multi-attacks. Static inspection found its five damage-dependent intent images still referenced remote URLs omitted from UI assets v1. Version 2 replaces only that image-source expression with embedded, genuinely downloaded public images. Native damage/hit calculation and thresholds are unchanged.

All five images passed download media/magic/size checks and local image decoding. The real rewritten overlay passed `node --check`; replacing the generated lookup with the original URL expression reproduced the original renderer entry exactly. The installed v2 ASAR is `69fd36df875ddd3f55ef751dff0cbb8e9c102654948e1849022ebd3b91ad6644`. Comparison against v1 found only `dist/renderer/assets/Sts2Overlay-DPeYNPLb.js` changed inside ASAR. Outer signing, fixed native payloads, original base/policy binding and the preferred v2 receipt were verified; legacy copy/receipt remain intact. No live process was restarted.

The full suite passed 252 tests; two additional installer publication/signing-failure regressions then passed within the 13-test updater suite. Coverage includes all five lookup entries, incremental asset preservation, rejected destinations/anchors, legacy/v2 selection, signing failure, idempotent installation and default tier seeding for both UI versions. Repository and diff checks passed. A visual combat check remains pending the next normal launch from the refinement checkout; the running diagnostic companion retains its previous image source.

## Dedicated Dock launcher — November 10, 2026

A native AppKit launcher was built, ad-hoc signed, verified and installed in the owner Applications folder. Its idle window displayed the three expected controls without launching a game. The full suite passed 272 tests, including new game-lifetime, owner cancellation, no-callback rejection, exclusive worker lock, validated private OAuth-file and GUI protocol coverage. The app snapshot includes UI assets v2 selection and the attack-icon repair. Dock pinning could not be automated because the Dock UI tool timed out; the owner can keep the running icon in the Dock.

This establishes build/startup UI and synthetic orchestration, not a completed GUI-driven game session or long-session reliability. Actual Steam readiness, browser sign-in, overlay display and normal exit through the new app remain owner-run live checks. The prior supervision failure remains unexplained and is not attributed to the former four-hour cutoff. See [desktop use and implementation](Desktop-Launcher.md).

## PR #3 review hardening — November 11, 2026

A sampled Brooks review of the refinement diff found two issues: native owner-stop finalization could overwrite an explicit cleanup failure with a success message, and native outcome/installer publication behavior lacked automated protection. The frontend now retains the terminal outcome independently of owner intent; a reported error or unreported nonzero exit remains visible. A close request also keeps the launcher open with the error rather than quitting after failed cleanup. The actual Swift finalization seam is compiled/executed in a macOS-only regression, while portable synthetic installer tests cover complete runtime snapshots, compile/sign/verify failures and existing-destination preservation. The builder compiles both Swift source files using an explicit application entry point.

These PR fixes do not replace a running installed app. Rebuild the launcher from the merged/reviewed code when updating the installed application. The native outcome test is explicitly skipped on non-macOS CI; portable worker, supervisor and installer tests still run there. A subsequent Codex review confirmed that independent pipe/exit callbacks could discard the final status. The native reader now drains stdout to EOF and queues data/error callbacks before finalization from a single producer. A compiled regression delays every UI callback until after worker exit across 20 child processes, then verifies all report bytes precede exit handling.

PR-review validation: all 276 tests passed locally, including the Swift outcome regression; the complete multi-file AppKit launcher compiled successfully. The native regression was rerun after adding explicit close-request/failed-cleanup assertions.

The output-ordering follow-up passed the native regression and complete AppKit compilation. Python behavior is unchanged from the 276-test pass; CI is rerun on each pushed head.

## Live startup status repair — November 11, 2026

The first startup of the rebuilt launcher appeared stuck on its initial checking message. Process/backup metadata showed that backup had completed and Steam was already open. A standalone Swift fixture using the actual `drainLauncherWorker` reader and a cat child reproduced the failure: `status_delivered_while_worker_waits: false`. The child emitted a short status then waited for input, isolating the problem from backup work and JSON parsing.

The prior review fix used Foundation `read(upToCount: 4096)`, which withheld the short pipe message until EOF or a full read. The native reader now uses interrupt-safe POSIX reads to deliver available bytes immediately, retaining the single-producer EOF-before-finalization ordering. A new interactive native regression failed before the fix (`status_before_worker_exit=false, clean_exit=true`) and passed afterward. The existing twenty-process final-message ordering regression also passes.

The stalled GUI worker was cancelled via Stop Companion and the app closed normally; no game was launched by the fixture or recovery. A signed updated launcher will replace the previous bundle after verification, retaining a private rollback copy. Steam may remain open from the cancelled attempt; the owner must allow Cloud synchronization and quit Steam before a fresh startup/backup.

Validation: all 277 tests passed, including both native pipe/lifecycle cases; AppKit compilation and rebuilt app signing/verification passed. The ordinary suite invocation initially selected an incompatible Intel Node binary, while the prior Homebrew native Node path was absent. The successful run used a temporary Node-only shim around the already verified companion's embedded Node v22.21.1; no global package, runtime policy or repository dependency was changed.
