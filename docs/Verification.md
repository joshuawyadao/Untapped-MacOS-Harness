# Verification and reward milestone

This record distinguishes static inspection, startup, game detection, reader attachment, state reading, and overlay display. Each requires separate evidence. The pinned user-supplied companion was `3.12.3-latest` with `app.asar` SHA-256 `ca3a2e6a6f728b2d635abfc70a5434d4107438b8d801a650357989e8442d798c`.

| Milestone | Result through November 2, 2026 | Evidence or next check |
| --- | --- | --- |
| Static inspection | Verified | Exact archive hash, guarded STS2 gates, bundled overlay/reader, and both Electron fuse wires `10110001` reproduced. |
| Source and preparation | Verified | Source signature valid outside the Codex sandbox; a copy-only patched session was prepared. Signature checks inside the Codex sandbox were misleading, so that environment is not used to judge vendor validity. |
| Offline policy | Smoke-tested | Real-home read, outside write, and remote IP socket denied; session write and loopback allowed. |
| Companion signing | **Verified after owner approval** | The owner separately approved outer-only ad-hoc signing for copy04 and copy05. Deep strict verification, both original entitlement sets, and fixed framework/native/ASAR hashes passed. |
| Companion startup | **Offline Core initialization logged** | Copy05's latest private attempt records manual acceptance and Fully initialized, with zero anonymous-token acquisition/retry lines. Terms visibility was confirmed by the owner. The run ended at its 45-second limit with no remaining copy05 processes. |
| Native game window detection | Untested | Requires a `window-detected` event from the copied companion. |
| Reader attachment | Untested | Requires `attach-attempt`, then `reader-connected` after vendor `connect()` reports success. The `status` label is `CONNECT_ACKNOWLEDGED`: native connection and runtime wrapper setup were acknowledged, but later game-context traversal remains unproved. Window detection alone is insufficient. |
| Reward state | Untested | Requires a real `reward` event with card IDs, upgrades, and normalized positions matching the visible game screen. |
| Overlay and recommendations | Untested | Need visual overlay evidence and separate advice validation; neither follows from a reward event. |

The initial preparation made no signing change; the outer signature was later changed only with explicit owner approval. No entitlement was added. During the protected runs no game was launched and no save was read. The owner manually accepted Terms on November 2; no account login or run upload was authorized or observed. Copy04 attempted anonymous-token acquisition, which failed under the offline policy; the adapted copy05 reaches logged Core initialization without those requests. Other metric requests still fail under the offline policy. The separate extra-launch incident below has unknown native profile effects. Forty-six synthetic tests passed, including Node VM execution of the original bootstrap against stubs, ten mocked signing tests, six startup-diagnostic tests, seven approved outer-launch tests, and three offline-authentication tests. Vendor code and native modules were not executed in that suite. The CI test job checks portable harness behavior and repository hygiene, not macOS game compatibility.

Before approved signing, the locked desktop prevented UI inspection but was not the startup cause. The unlocked inventory still showed no companion window. A process sample contained only `_dyld_start`, a 96 KiB footprint, and no loaded-image listing; a minimal Electron run-as-Node probe also stalled then. The OS log explicitly identified Gatekeeper rejection and assessments identified an invalid resource seal. After approved signing, the same runtime diagnostic succeeds. Nested helpers/frameworks verified. No OS warning was approved or bypassed.

## Companion-only signing

The owner approved re-signing **only the outer companion bundle** in copy04, then separately approved the same operation for copy05 after the offline credential adaptation. Both executions succeeded, retaining Hardened Runtime and the five existing true entitlements: debugger, JIT, unsigned executable memory, DYLD environment variables, and disabled library validation. Add no entitlement, including `get-task-allow`. Do not sign the game or recursively sign nested code.

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
