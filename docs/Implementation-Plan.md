# Plan

Build a reversible, version-pinned native macOS diagnostic harness around Untapped's existing STS2 reader and overlay, progressing toward one verified card-reward screen without altering the installed game or saves.

## Scope
- In: Python standard-library CLI, exact archive verification, guarded STS2 and startup-isolation patches on a disposable companion copy, offline startup diagnostics, synthetic regression tests, and separate evidence for startup, detection, attachment, state reading, and overlay display.
- Out: Vendor redistribution, Windows/CrossOver, replacement advice engines, global protection changes, automatic terms acceptance, account login/uploads, game launch or save migration, and signing/entitlement changes without specific approval.

## Action items
- [x] Read the handoff, pinned inspection record, README, CONTRIBUTING, SECURITY, governance, CI, and repository checks; reproduce static archive findings. No application tests or harness framework exist yet.
- [x] Create `codex/native-sts2-poc` and checkpoint this resolved plan before implementation.
- [x] Implement read-only inspection and fail-closed archive patching with original hashes, exact-match guards, integrity metadata, native binary/fuse observations, and copy-only preparation.
- [x] Add an isolated offline launcher with fresh settings/logs, memory-only credential shim, disabled updates/telemetry/login-item/protocol registration, and no real home/save access; preserve terms acceptance as a user action.
- [x] Capture only bounded diagnostic events needed for window detection, reader connection, and reward card IDs/upgrade levels/positions; add a strict comparison command against a manually transcribed real reward screen.
- [x] Add synthetic tests for malformed/changed archives, narrow patches, copy/source safety, launch isolation, and reward mismatches; run `python3 -m unittest discover -s tests -v`, Node syntax checks, repository hygiene, and `git diff --check`. Extend `CI Verify` for portable behavior tests; vendor code never runs in CI.
- [x] Attempt preparation and bounded offline startup on the pinned local artifact when safe; stop at any concrete signing/security/terms gate and record each unverified milestone. Never infer reward success from a visible UI.
- [x] Update README, CONTRIBUTING, governance, and focused architecture/verification docs with ownership, isolation limits, rollback, actual results, and the explicit game-profile strategy needed before gameplay.
- [x] Review staged files for vendor/private data, checkpoint coherent slices, and push this feature branch through save-branch. Do not open or merge a PR.
- [ ] Complete independent scaled-geometry and overlay verification. Debug-game install/menu, native detection/connection and real reward IDs/upgrades/order are now observed. Captured scale fields are missing; the owner confirmed no overlay appeared, and the vendor reward tree is login-gated in the empty offline profile.
- [x] Prepare a reviewable, opt-in outer-companion ad-hoc signing command and session-bound receipt guard, with synthetic tests. Do not execute signing until the owner explicitly approves the exact per-copy change. Preserve the five original entitlements, Hardened Runtime, nested code, and all game/OS protections.

## Open questions
- None for implementation. Runtime approval gates are explicit constraints: leave terms untouched and request separate approval for any concrete signing or debugging-entitlement change if evidence shows one is needed.

## Discovery notes

- Pinned companion: `3.12.3-latest`; ASAR SHA-256 `ca3a2e6a6f728b2d635abfc70a5434d4107438b8d801a650357989e8442d798c`.
- Both Electron slices have fuse wire `10110001`: embedded ASAR validation and ASAR-only loading are disabled in this artifact. The Info.plist header hash exists; changing sealed resources still invalidates the vendor bundle seal. Signing was initially excluded; the owner later approved the one-copy operation recorded below.
- Existing `UC_TEST_SANDBOX_DIR`, `UC_TEST_SANDBOX_ID`, and `UC_SKIP_UPDATE_CHECKS` hooks help, but do not alone isolate Keychain, telemetry, protocol handlers, or login items.
- No gameplay will be started automatically. A copied game does not isolate Steam Cloud or saves. The first runtime attempt can reach only startup/terms without a separately established gameplay/profile strategy.
- New original harness behavior warrants durable architecture/verification docs and synthetic tests; real captures and vendor files remain outside Git.

## Validation and runtime ledger

- Plan checkpoint: `383ce9e` on `codex/native-sts2-poc`.
- Twenty synthetic behavior tests pass across ASAR parsing/rewriting/integrity, copy safety, binary pins, credential/bootstrap isolation, reward comparison, connection truthfulness, and process-group cleanup. Bootstrap syntax and whitespace checks pass.
- Native artifact: archive, native reader, executable, framework hashes and both fuse wires reproduced. Pristine vendor signature verifies outside the Codex sandbox; the same check inside the sandbox misleadingly reports invalid signature, so no signature change was inferred or applied.
- Preparation succeeded in a new session outside Git. Only two packed JS entries changed; native binaries, Info.plist, installed game, signatures, and entitlements were not edited. The modified resource invalidates the copied bundle seal; no re-signing was performed.
- OS sandbox probes denied real-home reads, writes outside the session, and remote IP connections; allowed session writes and loopback. These finite probes are evidence for this macOS build, not a complete sandbox audit.
- First offline launch: 15-second limit reached, no bootstrap/ready/reward event, no stdout, and no companion log. Startup was NOT OBSERVED. UI inspection was unavailable because the Mac was locked; the causal reason for startup failure is unknown. Terms were not accepted and no game was launched. Attachment, traversal, state reading, and overlay remain UNTESTED.
- Independent review found two correctness issues, now fixed and regression-tested: a resolved `false` reader connection must not emit success, and descendants must be killed even after the probe leader exits. A true connection is labeled CONNECT_ACKNOWLEDGED; it does not prove readable game state.
- The original desktop-observation blocker is resolved; the per-copy signing proposal below was approved and executed, and a separate child-sandbox decision is now pending. One real card-reward match remains the acceptance milestone.
- Implementation checkpoint: `a2d46db`. A second preparation of the final guarded patches passed Node syntax checks for both changed vendor chunks; a full packed-entry comparison confirmed exactly two changed entries and the source hash remained pinned. No second launch occurred. No processes from the first probe remained running after cleanup.
- Documentation now covers runnable commands, architecture, evidence, reward comparison, and rollback. Vendor distributions, private sessions, and logs are outside the repository; no unrelated tracked changes were present at task start.
- Save result: `codex/native-sts2-poc` pushed successfully to this repository’s `origin`; the working tree is scoped to the harness task. Checkpoints include `383ce9e`, `a2d46db`, and `35a01d4`. Runtime acceptance remains pending as listed above.

## Resumed startup diagnosis

- Owner unlocked the Mac. An unlocked 45-second startup probe still returned exit 1 with NOT_OBSERVED and empty output. Native inventory showed no companion window.
- A second 20-second bounded reproduction was sampled at the same pre-JavaScript stall: only `_dyld_start`, 96 KiB footprint, and no loaded-image listing. A minimal `ELECTRON_RUN_AS_NODE` diagnostic also stalled without loading the companion JS. These were isolated diagnostic executions, not game tests.
- Targeted macOS logs identified the immediate blocker: `syspolicyd` reported a Gatekeeper prompt and then terminated the exact sampled probe for Gatekeeper rejection. Outside-sandbox `codesign --verify --deep --strict` and `spctl --assess --type execute` both identify the modified `Contents/Resources/app.asar` as an invalid sealed resource; nested code verified.
- The locked desktop was an observation limitation, not the startup cause. No security warning was approved or bypassed. No signature, entitlement, sandbox access, game/save state, or global protection was changed.
- Proposed next experiment: explicitly approved ad-hoc re-signing of only a fresh disposable companion's outer bundle, retaining its original five entitlements and Hardened Runtime; no recursive signing, new entitlement, game change, or automatic Gatekeeper exception. Ad-hoc identity is not vendor/notarized identity and may still need a separately handled OS decision.
- Resumed plan checkpoint: `7f855bb`. Added `harness/signing.py`, explicit `signing-proposal`/`sign-copy` CLI commands, a session-bound output hash receipt, and ten synthetic signing tests in `tests/test_signing.py`. All 30 tests pass; codesign mutation is mocked in tests. Default `sign-copy` was also verified to refuse with exit 2, leave the real prepared executable unchanged, and write no success receipt.
- Prepared the exact proposal for `/private/tmp/untapped-native-sts2-poc-04/Companion.app`, confirming both original architectures' entitlements. Only a proposed entitlement plist was written outside Git; no signing command was executed. Actual code-signing, ad-hoc Gatekeeper acceptance, reader attachment, reward state, and overlay checks remain pending.
- Updated README, CONTRIBUTING, architecture, and verification with the concrete Gatekeeper cause and approval boundary. Independent signing review found a lost-error-detail issue; bounded codesign diagnostics and a synthetic failure regression now preserve the actual reason without writing a success receipt.

## Approved companion-only signing experiment

- The owner explicitly approved ad-hoc re-signing only `/private/tmp/untapped-native-sts2-poc-04/Companion.app` and retrying offline startup. This approval retains Hardened Runtime and the five existing entitlements, with no nested signing, installed game/save changes, sandbox relaxation, OS-warning approval, or global protection change.
- Execute the already reviewed `sign-copy` command for that fresh session, verify signatures/entitlements and pinned nested payloads, then retry the bounded offline launch. Report each runtime milestone separately and retain terms/gameplay approval boundaries.

- Approved execution result: outer companion signing succeeded. Deep strict verification and both architectures' original entitlements passed; framework/native/ASAR pins remained unchanged. The private signing receipt records the new outer executable hash.
- Offline launch now emits bootstrap and Electron ready and exits 0 before Core initialization or UI. Its log reports a singleton lock failure; stderr reports socket-directory creation failure and child sandbox initialization EPERM. A minimal run-as-Node diagnostic succeeds under the unchanged outer policy (Electron 37.10.3, Chromium 138.0.7204.251). This verifies executable/runtime startup only, not a working companion UI.
- Separate synthetic Unix-socket binding inside the session returns EPERM because current network rules permit only IP loopback. Chromium also uses MAC_CHROMIUM_TMPDIR rather than TMPDIR for its temporary singleton directory. Plan a safe temp-directory redirect and truthful blocker diagnostics with synthetic regression coverage.
- Electron's child helper applies its own Seatbelt sandbox; the outer inherited Seatbelt profile conflicts with that initialization. No sandbox was disabled or relaxed during the approved run. A single-layer launch is a separate security decision; prepare its exact scope before requesting approval, without executing it.

- Safe implementation update: Chromium temp files are redirected to session `t/`. `status` separates Electron readiness, logged Core/terms milestones, socket-directory errors, and child-sandbox errors; launch returns nonzero for known blockers. Six new synthetic startup tests bring the full suite to 36 passing tests. No app/ASAR change or further signing was needed for these launcher/reporting changes.
- Prepared, but did not execute, an exact next launch for the same signed app with a fresh private profile and Chromium `--no-sandbox` while retaining outer confinement. A proposed Unix-socket rule is limited to the session path; synthetic probes allow that private IPC while denying outside-session socket connections, remote IP connections, real-home reads, and outside writes. The default launcher policy is unchanged. This next security tradeoff requires separate explicit approval.
- Independent review confirmed the next proposal retains the outer policy. It must use the bounded process-group runner, verify the signed copy before spawning, and stop after 45 seconds. Separate OS processes remain; the proposed loss is Chromium child sandbox restrictions. Remote outbound denial was tested; remote inbound behavior is not established by the bind probes. No probe processes remain running.

## Approved single-layer startup retry

- The owner explicitly approved a 45-second retry with Chromium `--no-sandbox` for the same disposable copy, retaining the outer sandbox restrictions and the reviewed session-path-only Unix IPC allowance.
- Execute only the prepared command/environment against the signed copy, with a fresh empty profile, preflight signature/hash checks, and process-group cleanup. Stop before terms acceptance, account login, OS permission approval, or game launch. This approval does not relax filesystem, remote networking, Keychain, or global OS protection boundaries.

- Approved single-layer result: private logs show App starting, Core creating/showing its main window, updater checks skipped, and Core Showing Terms of Service. The process remained until the 45-second limit and was stopped by the bounded runner. Bootstrap and ready events were recorded. No terms were accepted and no game was started.
- UI-inspection incident: `getState` observed the approved app running, but `getApp` timed out after the probe ended and appears to have reopened the copy through LaunchServices. Three new exact-path processes were then detected outside the runner, with helper arguments pointing at the normal companion profile. They were stopped as soon as detected; none remain. No normal-profile contents were inspected or deleted, and native cache/profile effects from that extra launch cannot be ruled out. Do not claim that all companion-profile state remained untouched. Avoid UI APIs that can launch or reopen the app; use non-launching inventory and manual user interaction instead.
- Implement a reproducible explicitly approved `launch-outer` CLI path with a fresh private attempt profile, the same outer restrictions and session-only IPC, signed-copy checks, bounded process-group cleanup, and recorded evidence. Add synthetic tests for approval gating, fresh data, command/policy constraints, and cleanup. No further live retry or UI-opening call is authorized or needed to implement this command.

- Implementation: `launch-outer` now formalizes the approved mode, refuses without the explicit approval flag, requires a signed copy, reuses the existing hash/signature validation, and creates a fresh unique private attempt directory. Its outer policy retains original constraints and session-only Unix IPC; no UI app-opening API is used. Six synthetic tests in `tests/test_outer_launch.py` cover approval gating, receipt/validation failures, fresh settings, flags/environment/policy, timeout cleanup, and CLI dispatch. All 42 tests pass.
- Updated README, CONTRIBUTING, SECURITY, architecture, and verification with the repeatable CLI, protected Terms milestone, unresolved visual/manual Terms step, and the corrected extra-launch incident. No normal-profile data was inspected/deleted; native cache effects from the extra launch remain unknown. A user-readiness question for manual Terms review is pending; no additional live probe is launched just to inspect UI.
- Final review identified a diagnostic gap: an early ready event followed by a nonzero process exit must return failure even without a recognized log string. Add that regression before saving the approved launcher.
- Final review fix: nonzero process exits now fail the launch CLI even after an early ready event; a synthetic regression covers both launch modes and distinguishes a bounded timeout. All 43 tests pass. The approved private profile records acceptedTOS=false. Normal-profile contents were not read.

## Manual Terms review on November 2, 2026

- The owner confirmed readiness for manual review. Ran the existing `launch-outer` command on the same signed copy with the approved 45-second limit, a fresh private attempt, and unchanged outer restrictions. No app-opening UI API was used.
- The owner accepted Terms in the window. The private attempt `outer-attempt-mn7n35o2` records `acceptedTOS=true`, and its log records Terms accepted/continuing initialization. This state belongs only to that private profile; another `launch-outer` invocation creates a fresh profile and does not preserve it.
- After acceptance, anonymous upload-token requests failed with `ENOTFOUND` and retried under the offline policy. Core logged Loaded all accounts, but not Fully initialized before timeout. No detection, attachment, or reward event was emitted; overlay behavior remains unverified. Do not enable remote networking or fabricate credentials to advance initialization.
- The runner reached its 45-second limit and cleaned up. A subsequent exact-copy process check found none running. The installed game was not launched, and no game/save or normal companion-profile data was read.
- Update the current README, architecture, and verification status with this result. These evidence-only documentation changes do not change executable behavior or require new automated tests; verify repository hygiene and whitespace. Inspect the pinned post-Terms startup path read-only before proposing a next experiment.

## Offline credential-acquisition adaptation

Static inspection confirms `initializeAfterTos()` awaits two authentication calls and onboarding before enabling STS2. Each can acquire an anonymous token with 14 seconds of retry backoff; the nominal account timeout starts after the authentication awaits. Native reader construction has no account requirement. The recorded offline failures are expected network confinement, not evidence that authentication succeeded or that the reader is incompatible.

- [x] Checkpoint the runtime evidence and this resolved follow-up plan before changing executable code (`2200164`).
- [x] Add one exact guarded Services-chunk patch: when `UNTAPPED_HARNESS_OFFLINE=1`, `ensureLocalCredentials()` returns empty authenticated credentials and null anonymous credentials before credential reads or token requests. Preserve its ordinary path, Terms flow, account feature gates, reader implementation, and outer network denial; never invent a credential or authenticated account.
- [x] Add `tests/test_offline_auth.py` with executable synthetic method tests for unavailable authentication, no credential reads/requests/writes, repeated callers, and unchanged non-offline behavior. Check anchor rejection and Services archive integration. Vendor code must not enter the test suite.
- [x] Reapply current patches to the pinned archive privately, check all three changed JS entries and their syntax, and confirm all other packed entries and native payloads remain unchanged. Preparation is reversible; do not sign or launch a newly modified copy under the earlier exact-copy signing approval.
- [x] Update README, architecture, and verification with the adaptation and its untested native status; run targeted/new tests, full portable suite, Node syntax, hygiene, and whitespace. Save this validated slice through the branch workflow.
- [x] Prepare the exact companion-only signing proposal for a fresh disposable copy if the pinned source is still available. At this checkpoint copy05 was unsigned/unlaunched; its proposal preserves the original five entitlements and Hardened Runtime. The subsequent approval and execution are recorded below. Real-game/save strategy remains a separate execution gate.

- Validation: the three new synthetic tests failed before the guard and passed afterward. All 46 tests pass, bootstrap and all three patched vendor JS syntax checks pass, and exact packed-entry comparison preserves every other entry. Fresh copy05 has patched ASAR SHA-256 `e102b9c5c4369e4d995a7d5ebf1e06a4f81aa042f12172d729e0886c373d3e4f`; native/executable/framework/plist hashes are unchanged. No new signing or launch occurred. The source DMG was detached. Independent read-only review found no issue in the empty-credential consumers or guarded archive integration.

## Approved copy05 startup experiment

- The owner approved the reviewed outer-only ad-hoc signing proposal for `/private/tmp/untapped-native-sts2-poc-05/Companion.app` and another 45-second protected startup. Preserve the five original entitlements, Hardened Runtime, nested payloads, and existing outer sandbox restrictions, with the previously reviewed Chromium `--no-sandbox` mode and session-only Unix IPC.
- Run the existing `sign-copy` command, then `launch-outer` with a fresh private profile after signature/hash validation. Leave Terms acceptance to the owner; do not use app-opening inspection APIs, start the game, access normal profiles/saves, enable remote networking, or approve OS prompts. Record full initialization separately from Electron ready, detection, attachment, reward state, and overlay evidence.
- Signing succeeded. Deep strict verification, both original entitlement sets, and unchanged native/framework/ASAR pins passed. The private receipt binds signed executable SHA-256 `daffa1ea0eb5fbb20eb7035f43a5d9224787feef3c566b2dbd7826cc353c866e`. No nested code was re-signed and no entitlement was added.
- The protected run used fresh private attempt `outer-attempt-jft7ntme`, recorded bootstrap and Electron ready, and logged Showing Terms of Service. No acceptance was recorded in that attempt (`acceptedTOS` absent), and no post-Terms full initialization, detection, attachment, or reward event was observed. Copy04's earlier acceptance remains separate. This does not test the new offline credential branch beyond syntax/synthetic behavior.
- The runner reached its 45-second limit and stopped its process group; an exact-copy process check found no remaining copy05 processes. No app-opening inspection, game launch, normal profile/save access, remote permission, or OS protection change occurred. A user readiness/window-visibility question is pending before another manual Terms window; the same copy's signing and protected mode are already approved.
- Update current README, architecture, and verification with this outcome. No executable or test behavior changed during this runtime evidence slice, so no new tests are needed. The previously passing 46-test suite remains the portable validation; run hygiene and whitespace checks before saving the documentation.
- The owner requested another 45-second window using the same approved copy/mode. Fresh attempt `outer-attempt-bs1oj8lo` again recorded bootstrap/ready and Showing Terms of Service, with no acceptedTOS value or post-Terms milestone. It ended at its limit; the exact-copy process check found none remaining. The owner confirmed seeing Terms with an Accept button, establishing manual visibility. Whether Accept was clicked and what followed is now the pending clarification; do not repeat a readiness-only retry without resolving that distinction.

## Confirmed offline initialization and isolated-game planning

- The owner clarified that Accept had not yet been clicked. Reopened the same approved copy/mode for 45 seconds with fresh private attempt `outer-attempt-7g7qo6mz`; the owner then accepted Terms. Its config records `acceptedTOS=true`, Core logged Terms accepted and Fully initialized in the same second, and no anonymous upload-token acquisition/retry line appeared. Status reports `CORE_INITIALIZED_LOGGED`. Other metrics requests failed under the unchanged offline policy; this does not establish authenticated functionality or the absence of attempted networking.
- The runner reached its time limit, cleaned up its process group, and no exact-copy processes remained. Events contain only bootstrap/ready. No game was launched or detected, no reader connection/reward was observed, and overlay behavior remains unverified. Prior private attempts and their evidence were preserved.
- The owner chose **Plan an isolated test profile first**, rather than observing normal manual gameplay. Complete read-only planning only: inspect installed distribution metadata/argument behavior, companion save versus memory dependencies, and primary Godot/Valve guidance. Do not create an OS account, copy game artifacts, launch a game, inspect saves, or change Steam settings in this pass.
- Read-only discovery found actual `--force-steam=off --nomods` flags, no verified game-specific save-root override, and process-only reward fields independent of save/history files. A custom save directory by itself would not establish Cloud isolation; a separate OS user does not establish cross-user reader access. Recommend both apps in one dedicated standard test account and graphical session, with fresh data and no Steam initialization, subject to bounded runtime validation.
- Add [Isolated-Game-Plan.md](Isolated-Game-Plan.md) with the resolved recommendation, ordered setup/launcher-validation/gameplay steps, exact execution gates, stop conditions, and cleanup. Update README, CONTRIBUTING, architecture, and verification to reflect successful offline Core startup and the unexecuted game plan. This slice changes documentation only; the prior 46-test suite remains applicable without new cases or a redundant rerun. Run repository hygiene and whitespace checks, then checkpoint and push the evidence/plan.

## Approved isolated-test implementation

The owner approved isolated account setup and game launch, and will create/log into the standard test account when instructed. This resolves setup/first-boot execution gates; no repeat approval is needed for the planned 60-second confined probe. No new game entitlement/signing change is authorized.

- [ ] Implement a standalone guarded game preparation/launch module and synthetic tests, including ownership, build/hash checks, no-Steam/no-mods command, original-home denial, private writes, bounded cleanup, and refusal outside the test account.
- [ ] Implement an optional exact target-PID guard before STS2 connection, with executable synthetic tests; preserve startup-only operation without a target. Prepare any changed companion's signing proposal before requesting the distinct signing change.
- [ ] Update isolated-game plan, README, verification and account runbook; run targeted/full tests, Node syntax, hygiene and whitespace, then save branch.
- [ ] Have owner create/login to a fresh standard account; perform copying and first game probe only there. Validate private data and no Steam before gameplay.

No implementation open questions remain. Account creation/login is a required manual execution step.

### Isolated launcher implementation result

- Added `harness/game_launch.py` and eight synthetic tests in `tests/test_game_launch.py`: pinned build and complete file/mode/symlink manifests, unchanged signatures, standard-account ownership checks, Steam/game conflict monitoring, private policy, and 60-second process-group cleanup. Normal-account preparation refused before source access. Native execution remains blocked on manual test-account login.
- Added STS2 pre-construction PID/user/executable verification in bootstrap and guarded Core patch, with two executable synthetic tests; CLI target preflight has three additional tests in `tests/test_target_launch.py`. Rechecks reduce target substitution risk; a residual race remains between identity inspection and native connection. The changed companion has not been packaged/signed/launched.
- All 59 tests pass; Node and account-script syntax pass. Dummy OS-policy probes allow private writes and deny original-home reads, outside writes, and remote sockets. Initial probe could not import Python modules from its protected inherited cwd; using the actual planned private cwd passed. These finite probes do not verify native game data paths.
- Staged a game-only tar and original harness sources at `/private/tmp/untapped-sts2-transfer-01`, with a SHA-256 transfer check and manual test-account script. No saves, Steam settings, private profiles, credentials, or Git data are included. Added `docs/Test-Account-Runbook.md`; original game and normal saves/settings were not modified. User was directed to MacBook System Settings (not app settings) to create a Standard account.
- Account setup/game launch are already approved. Next required action is owner creation/login to `sts2test`, followed by the staged Terminal script there. No further setup/first-boot approval is needed. Actual Steam absence, data paths, game window, cleanup, attachment, reward, and overlay remain unverified.

## Window visibility diagnosis

The owner ran the test-account first boot and saw no menu. Exported diagnostics confirm `./SlayTheSpire2` as the data root (relative to the private session cwd), Steam initialization skipped, intended no-Steam/no-mods arguments, and both essential/complete main-menu load milestones. The shader-cache error did not prevent these milestones. Shutdown static-string errors alone do not establish a startup failure.

- [x] Add explicit windowed mode, 1280x720 size, and on-screen position to the same bounded probe; preserve sandbox, account checks, game hashes/signatures, and 60-second bound. Extend the existing command test and run full tests.
- [x] Stage an account-owned helper refresh/retry script that reuses the existing private game session without re-extracting or overwriting the game/data. Update runbook/verification; validate syntax/hygiene, commit and push.
- [x] Owner runs the retry in sts2test and confirms actual visible UI. Visibility, actual file confinement/cleanup and reader compatibility remain separate pending checks. No open implementation questions.

- Visibility probe prepared: explicit windowed/always-on-top, 1280x720 at 80,80; existing command regression updated, all 59 tests and retry-script syntax pass. Added repeatable helper-only refresh/retry script and documented the logged menu milestones separately from visible UI. Same confinement, game hashes/signatures and 60-second budget retained. No native retry was run from the normal account.

## Fresh visible game and reward-test preparation

The owner confirmed the windowed retry showed the main menu, allowed fullscreen/settings/back navigation, then closed, and appeared to contain fresh game data. The prior launcher report reached its timer limit; the new close is consistent with the same 60-second supervisor, not independently proved to be a crash. No Steam or imported progress was reported; exported first-boot logs establish Steam skipped and private relative data root. Full cleanup/reader compatibility remain separate checks.

- [x] Add an explicitly selected manual-play mode with a maximum 900-second bound; preserve the default maximum 60-second first-boot mode and all isolation/hash/process checks. Test refusal outside limits and correct bounded manual dispatch. No long native run until the owner agrees the prepared manual-play step.
- [x] Prepare the current guarded companion from the pinned source as fresh copy06, verify changed JS syntax, and produce its exact original-entitlement outer-only signing proposal without executing it.
- [ ] Update runbook/verification, stage a helper-only manual-play script, validate and save. Ask for the new concrete companion signing decision and agreed bounded manual play only after these artifacts are ready. Existing setup/first-boot approval persists. No new game signing/entitlements authorized.

No implementation open questions remain.

- Preparation result: manual-play is explicit and bounded to 900 seconds; default60 remains. Three new boundary/dispatch/deadline tests bring the suite to62 passing cases. Updated/staged helper-only play script. Copy06's exact original-entitlement signing proposal is ready; all three changed JS entries pass syntax and every other packed entry/fixed payload is unchanged. New signing and long native execution remain unexecuted. Source image detached. Runbook/verification updated; no game or global security change occurred.

## Approved guarded reward experiment

The owner explicitly approved copy06 outer-only signing, the same outer-confined 45-second reader observation, and up to 15 minutes of isolated manual game play. Preserve original entitlements/Hardened Runtime, game bytes, existing remote/home restrictions and target identity guard. No further approval is needed for these exact steps; new game/debugging entitlements remain excluded.

- [ ] Sign/verify copy06; transfer only its app, static manifest and signing receipt (no profiles/Terms/logs) with integrity check.
- [ ] Prepare test-account reader script: require sts2test, validate one copied-game PID/user/path, invoke guarded launch-outer for45seconds, and bound cleanup. Test script helpers with synthetic data and syntax checks; update runbook/evidence and save branch.
- [ ] Owner starts the approved manual-play script, reaches a reward without choosing a card, then runs the reader script in a second Terminal. Terms acceptance remains manual; no prompt approval or automatic play. Inspect private evidence before claiming attachment/reward/overlay success.

No implementation open questions. Native observation waits on the owner's reward screen readiness.

- Execution preparation complete: approved copy06 outer-only signing succeeded, deep strict verification and both five-entitlement sets passed. Signed executable SHA-256 `4e4a9e38726ca8fa160a68879e0db279d7fc95c363b95fd1cf8f0be3115b2ac1`. App/static manifest/receipt archive and SHA check staged without profiles/Terms/logs.
- Added `harness/reward_probe.py`, four synthetic tests in `tests/test_reward_probe.py`, and the test-account observation script. It requires one exact same-user copied game, rejects Steam/ambiguous targets, and invokes the approved 45-second outer launcher. All 66 tests pass. Runbook updated and scripts staged; native observation waits for the owner's paused reward screen. No game signing, entitlement, or global protection change occurred.

## Verified test-account home correction

The manual-play attempt returned -10 (SIGBUS). Its exported stdout ends during early asset/localization loading, with no useful native stack; the owner found no matching Apple crash report. Do not attribute SIGBUS to shader caching without a successful comparison run. Independent defect: the constructed environment omits HOME. Godot4.5.1 macOS get_config_path/get_cache_path read HOME and otherwise fall back to a relative path, consistent with blank HOME and `./SlayTheSpire2` in the exported log.

- [ ] Extend the existing executable-launch regression to require HOME from the validated pwd test-account home, even if parent HOME points at the normal account; reject inherited Steam/preload credentials. Observe failure before the correction.
- [ ] Restore normal HOME semantics only in the game child environment, using the already verified actual sts2test home (not an arbitrary redirected home and not a shell HOME assignment). Preserve sandbox, game bytes/signatures, target checks and bounds. Record that source in report.
- [ ] Update runbook, architecture and verification with the newly expected test-account user-data root; preserve prior relative test data without migration/deletion. Stage the existing60-second helper retry, run focused/full tests, shell syntax/hygiene and save branch.
- [ ] Owner performs a60-second controlled test before resuming15-minute play. Check actual data path, shader-cache warning and native stability. SIGBUS resolution remains unverified.

No implementation open questions. No new security/access change or game signing is involved.

- Home correction implemented: the launch regression failed on missing HOME, then passed with the verified test home despite a deliberately unsafe inherited HOME/Steam/preload environment. All 66 tests pass. Added a helper-only 60-second diagnostic script which exports its exact report and bounded, volume-filtered log automatically. Runbook/architecture/verification updated, old relative data preserved, no native retry run. SIGBUS causality and resolution remain unverified pending owner comparison.

## Companion helper-discovery comparison

The first test-account reader run returned -5 (SIGTRAP), with only native Electron FATAL Unable to find helper app and no bootstrap/ready/attachment evidence. A read-only transfer audit found all 333 archive entries, all141 file hashes/modes and14 internal symlinks match source, including all four helpers. A compiled inert Foundation bundle lookup under the home-deny/session-allow policy passed both confined/unconfined; this does not reproduce the actual vendor failure. No matching targeted system-log denial was found. Root cause remains unconfirmed.

- [ ] Compare the same signed copy06 bytes in a short private /private/tmp/uc-sts2-UID-* session, with owner/mode/symlink/path guards, fresh settings and unchanged outer restrictions. Earlier successful companion startup used private tmp sessions; this is a layout diagnostic, not a proved fix. No signing/game/entitlement change.
- [ ] Extend reward helper to permit only private owned sessions in that constrained temp namespace as well as its existing home path, and provide a startup-only45-second diagnostic requiring no running game/Steam. Add meaningful path/identity/mode/dispatch tests; missing target still cannot attach.
- [ ] Stage a one-command test-account diagnostic which verifies/extracts the existing signed archive into a new0700 root and exports exact attempt report/stdout. Preserve old data/profiles. Update runbook/verification, full tests and syntax/hygiene, checkpoint/push.
- [ ] Owner executes the diagnostic without restarting the game. Actual helper discovery/visible startup and later native attachment remain unverified.

No implementation open questions; existing copy06 protected-probe approval applies.

- Prepared comparison: shared private-session validation supports only the existing test home or owned 0700 canonical `/private/tmp/uc-sts2-UID-*` roots. Startup-only requires no Steam/game and provides no attachment target. Three new synthetic cases bring total to 69 passing tests. Diagnostic script verifies/extracts the identical signed archive, runs 45 seconds, and exports exact report/stdout plus inert helper metadata inside/outside policy. Old sessions preserved. Script/snapshot syntax passed; staged copies ready. No vendor comparison executed and no signing/protection change performed.

## Private-temp companion startup observed

The owner-run comparison reached ELECTRON_READY and TERMS_LOGGED with no recognized startup blockers, and hit the 45-second bound. The exported report identifies `/private/tmp/uc-sts2-502-hchi62ym`; inert helper checks pass inside/outside policy, all four executables mode 0700 after test-account extraction. The owner saw Terms. This establishes startup in that layout, not the precise cause of home-rooted lookup failure or reader compatibility. A clarification about whether the reported untapped.gg page was the companion window or a separate browser is pending; no further native execution occurs while that distinction is unresolved.

- [ ] Promote fresh short private-tmp sessions to the staged reward-observation script (same signed archive, owner/mode guard, policy, PID checks and 45-second bound). Preserve earlier home/tmp sessions.
- [ ] Automatically export the exact observation report, bounded stdout/Core log and whitelisted event data, so failures and any reward snapshot can be inspected without photo transcription. Use existing validated helper/CLI interfaces; shell/embedded Python syntax and69 tests provide verification.
- [ ] Update runbook/verification/README and save branch. Reward observation still requires owner-controlled game session, paused reward, manual Terms choice, and clarification of window type.

No implementation open questions; window-type clarification is an execution check.

- Window clarification resolved: the owner saw the Untapped companion window. Short private-tmp startup is confirmed by readiness/Terms and bounded completion; inert helper checks passed inside/outside policy. Updated the observation script to fresh private tmp roots plus exact report/event/bounded-log export, using existing validated interfaces. All 69 tests and script/embedded-Python syntax pass. Staged script updated; actual reward observation awaits owner-controlled game/reward readiness. No app bytes, signature, entitlement, or policy change.

## Guard execution failure and unprivileged identity helper

The owner-run reward diagnostic records Core initialized and window-detected, then our target guard throws spawnSync /bin/ps EPERM before any native reader construction/connection. This is not evidence of game attachment entitlement failure. /bin/ps is mode4755. A bounded same-policy reproduction denies its execution; a byte-identical non-setuid private copy is killed by OS validation and was discarded without re-signing or bypass. An original compiled libproc metadata probe succeeds under the identical policy, returning only the calling user's target UID/executable. No vendor code executed in these probes.

- [x] Add original Darwin C identity helper and a stdlib compiler/preparation module with clean environment, private owned0700 output, binary hash record and failure checks. Use public proc_pidinfo/proc_pidpath, refuse different users, validate canonical positive PID and compare process start metadata before/after to reduce PID reuse races. Test construction/failure and native own-process metadata without vendor code.
- [x] Update CLI targeted probes to build this helper in the fresh profile before launching. Update bootstrap to validate private helper ownership/mode/hash and call it instead of /bin/ps. Preserve PID/user/path matching, outer policy and guard-before-reader. Extend executable JS guard and CLI regression coverage; startup-only remains usable.
- [x] Prepare fresh companion copy07 from pinned source, validate exact JS changes, native pins and syntax, and produce the same original-entitlement outer-only signing proposal. Do not execute new signing before the owner approves this exact changed copy.
- [x] Update runbook/architecture/verification/README and prepare refresh scripts (defer live staging until signed-copy approval); run all tests, native dummy policy check, syntax/hygiene; commit/push. Actual reader connection remains untested until a future approved signed-copy observation.

No implementation open questions. No game entitlement, global protection or policy relaxation is proposed.

Implementation: original libproc helper, private compiler preparation, hash/file-checked bootstrap dispatch and targeted-launch build are complete. All 75 tests pass, including native own-process compilation/metadata. The production helper also passed an unchanged-policy inert target probe. Fresh copy07 and exact signing proposal are prepared without signing or vendor execution. Original5 entitlements and Hardened Runtime are retained in the proposal. Live transfer refresh and archive07 creation are deliberately deferred until signing approval; existing copy06 transfer is intact. Actual attachment/reward/overlay remain untested.

## Approved copy07 signing and protected retry

The owner explicitly approved copy07 outer-only signing and another 45-second protected observation, retaining the five original entitlements, Hardened Runtime and outer sandbox. The already-approved isolated manual-play allowance remains 900 seconds; game bytes/signing and global protections remain unchanged.

- [x] Execute the existing reviewed sign-copy command and verify both entitlement sets, deep signature and pinned nested/archive bytes.
- [x] Stage app/manifest/receipt-only companion07 archive with checksum and refresh original harness sources/scripts without profiles, Terms, logs or credentials. Verify transferred contents and source syntax.
- [x] Record results in verification/runbook, save the branch, and provide the manual test-account commands. Actual reader/reward/overlay evidence awaits the owner-run probe.

No open questions; approval applies to this exact copy and bounded experiment. No executable source changes are planned in this slice, so existing 75 passing tests remain applicable; use actual signing/archive integrity verification and repository checks.

Approved execution: copy07 outer-only signing succeeded; deep strict verification, both original entitlement sets, Hardened Runtime and nested/archive pins passed. Signed executable SHA-256 `6bfc801a5aece768b08c643c88759405b08ab8e4663a3e7b53841d09cb6ecb78`. Staged companion07 archive contains exactly app/manifest/receipt (333 entries), every archived file/symlink matches the signed source, checksum verified. Original helper sources and observer/startup scripts match repository bytes and pass syntax checks. No fresh vendor execution occurred in this staging step; the owner must run the observer in UID502's graphical account. Prior 75 passing behavior tests remain applicable; no source/test changes were needed for signing/staging.

## Controlled original-process attachment diagnostic

Build a minimal original target/inspector pair to distinguish target debugger entitlement from outer-policy restrictions after copy07's native connect returned false.

### Scope
- In: Fresh private temporary original-code fixtures, game-equivalent four entitlements/Hardened Runtime, one target differing only by get-task-allow, inspector with the companion's five entitlements, bounded same-user task-port acquisition inside/outside the unchanged outer policy, explicit result classification and cleanup.
- Out: Game/companion launch or signing changes, arbitrary PID attachment, memory reads/writes, OS prompt acceptance, global protection changes, or claiming vendor compatibility from dummy success.

### Action items
- [x] Add original C target (ready signal and bounded lifetime) and inspector (validate exact same-user fixture path/PID, acquire/deallocate task port only, return bounded structured result).
- [x] Add Python build/sign/verify and bounded matrix runner in a fresh private tmp root; keep native execution opt-in and prevent arbitrary input targets. Fail on build/signature/readiness/timeout anomalies, verify target liveness and clean up every target group.
- [x] Add portable regression tests for classification, failure handling and command/policy construction; keep native signing/probing out of CI. Review false-positive interpretation and prompt/cleanup boundaries.
- [x] Run the controlled matrix locally using only original fixtures, retaining exact return codes and unchanged-policy hash; distinguish denial, timeout and inconclusive controls. Never approve a prompt.
- [x] Update README, architecture, runbook and verification with result/limits, run full tests/syntax/hygiene, then commit and push the feature branch. Prepare any further game-copy proposal only if the evidence supports it, without executing it.

### Open questions
- None. The owner authorized the controlled original-process diagnostic. Signing any game copy remains a separate decision.

Discovery: copy07 observed window and attach-attempt, but core log reports native connect false; no state/reward events. Original game is ad-hoc Hardened Runtime with four entitlements and lacks get-task-allow. The native reader imports task_for_pid and memory-read functions. A narrow OS log query produced no denial messages and does not identify the failure cause. Existing 75 tests pass; fresh native experiment is necessary because synthetic tests cannot establish OS task-port behavior.

Result: original C fixtures and opt-in Python runner are implemented. Native matrices in UID501 reproduced denied code5 without get-task-allow and acquired code0 with it, both outside/inside the unchanged companion policy. All targets stopped, no memory read/write and no game/companion change. Seven new portable tests bring the full suite to82 passing; native fixture runs remain separate from CI. A standard-account diagnostic script and matching original sources are staged with syntax/byte verification. Next runtime evidence requires the owner running that script in UID502; no gameplay retry or game signing is requested in this slice. Updated README, architecture, runbook and verification describe exact findings and limits.

## Separate debug-enabled game-copy proposal

Prepare a new disposable copy and exact outer-game signing proposal after the UID502 original-fixture matrix also denied code5 without get-task-allow and acquired code0 with it, both inside/outside policy. Signing and runtime remain excluded until separately approved.

### Scope
- In: Copy-only preparation from the verified installed pinned game; exact original four entitlements plus get-task-allow; outer-only ad-hoc proposal retaining Hardened Runtime; source/tree/signature checks; explicit signing API/receipt for later approval; isolated test-account installation and launcher/reader guards for the distinct debug game path; portable tests and documentation.
- Out: Executing game signing or launching either app now, modifying either existing game copy or saves, weakening sandbox/Steam/normal-account checks, new companion patches, OS prompt acceptance or global protection changes.

### Action items
- [x] Implement game_debug.py copy/proposal/explicit-sign/receipt/verification/install interfaces with fail-closed tree/path/identity/entitlement checks. Restrict signing changes to outer executable and its resource seal, preserve all other bytes/modes/symlinks and baseline evidence.
- [x] Extend existing game launcher and reward helper with explicit debug-copy opt-in, exact separate path and verified receipt; retain default original-copy behavior and all isolation/timeout/Steam/PID guards.
- [x] Prepare dedicated install/play/observe scripts for later staging, never enable them before signed-copy verification. No original test profile or Terms is transferred.
- [x] Add portable signing/proposal/tampering/receipt and dispatch regressions, run targeted and full tests, syntax/hygiene. Native signing remains mocked; no test executes vendor code.
- [x] Prepare the real new unsigned copy and exact JSON signing proposal outside Git, verify pristine source/copy equality and reviewable proposed command/entitlement delta. Do not sign it.
- [x] Update README, SECURITY.md, architecture, runbook and verification with UID502 evidence, copy scope, guard behavior and pending approval; commit/push, then request approval for the exact prepared copy and bounded experiment.

### Open questions
- None for preparation. Actual signing of the new game copy remains a separate approval boundary.

Preparation result: new unsigned source-matching game copy and exact proposal are ready at /private/tmp/untapped-sts2-debug-game-01; all440 entries match the full original-tree pin. Both architectures' original settings and deep signature verify. Unapproved sign command refuses exit2 with unchanged executable/no receipt. Nine game-debug plus four dispatch regressions bring total to95 passing tests; syntax checks pass. Added SECURITY.md guidance after identifying the new per-copy debugger-access boundary. Scripts are ready in the repository but live staging and any game signing/launch remain pending separate approval; existing transfer/game copy untouched. The test game will keep using UID502's existing test data.

## Approved debug-game signing and bounded test staging

The owner explicitly approved signing `/private/tmp/untapped-sts2-debug-game-01/SlayTheSpire2.app` with the reviewed outer-only command, preserving original four entitlements and Hardened Runtime and adding only get-task-allow. Approval covers the 60-second boot check, up to900 seconds owner-controlled play and a protected45-second reader observation. It does not authorize OS prompt acceptance, normal save access, global protection changes or nested signing.

- [x] Execute the reviewed sign command, verify both architectures/settings/deep signature, allowed signing-only diff and unchanged installed source.
- [x] Archive only app/baseline/receipt with per-entry and checksum verification; refresh original source/scripts in the transfer without profiles, saves, Terms or credentials.
- [x] Record signed-copy/staging evidence and runbook status, validate syntax/hygiene and save the branch; provide the install/60-second boot commands for the standard test account. Actual game/reader evidence awaits owner-run tests.

No open questions. Existing95 passing behavior tests cover this implementation; this slice uses actual signing/tree/archive verification and script/repository checks, without new executable source changes.

Approved execution result: outer-only signing succeeded. Both architectures retain ad-hoc Hardened Runtime and the exact original four entitlements plus get-task-allow. Exactly the executable and CodeResources hashes changed; all other tree entries, file modes and symlinks match baseline. Signed executable hash74ba017ccac7626b9f269f8d2bf31dc2d185c64442bb18d5fa9a2abe910c6b63. Installed source still matches the full original pin. A443-entry app/baseline/receipt-only archive was verified entry-by-entry (file bytes/modes and symlink text) and by checksum288503d9974b4e9d8c5c7917851187cf33bec3a46a17d1bca7c6d619fca1e8e4. Original helper sources and install/play/observer scripts are now staged with byte/syntax verification. A final native verify command passed. No vendor application was launched; installation and boot/reward evidence await the owner in UID502. No executable source/test changes in this slice; prior95 tests remain applicable.

## Preserve signed transfer modes during private extraction

The owner-run installer stopped before installation with signed-tree mismatch. A tiny inert archive reproduced tar -xf applying umask077 (0755 becomes0700). Compare real archive byte/mode deltas before fixing; never relax receipt verification or re-sign the game.

### Scope
- In: Exact-mode extraction into a fresh owned private directory, inert archive regression reproducing the installer's umask, updated staged installer/helper and verification/runbook evidence.
- Out: Changing signed payload/receipt, new signing, game launch, overwriting partial sessions or inspecting the other user's private home.

### Action items
- [x] Confirm the real archive mismatch is exclusively file modes, preserving content hashes and entries.
- [x] Add a bounded private transfer extractor preserving recorded permissions; use it in the installer and test under umask077 with a real inert archive.
- [x] Prove default extraction fails and fixed extraction matches the signed receipt with the unchanged real archive; preserve failed private extraction for the owner and keep the destination-new guard.
- [x] Update verification/runbook, run focused/full tests and syntax/hygiene, stage original fix, commit/push and provide the same install retry command. Existing signing/test approval remains valid.

### Open questions
- None. This corrects original transfer code without changing vendor bytes or signature scope.

Result: exact installer extraction reproduced427 permission-only mismatches in the unchanged real archive (all bytes/entries matched). Added private bounded exact-mode extractor and wired installer; the new inert regression failed before -xpf and passes afterward. Three new tests bring total to98 passing. Fixed real extraction under umask077 passed all440 signed entries plus native deep signature/entitlement/receipt verification; no re-signing or vendor execution. Staged only original helper/installer fix with parity/syntax checks; failed UID502 extraction preserved. Updated architecture, verification and runbook. Owner must retry installation in UID502, then run the already-approved60-second boot check.

## Record first native reward read without overstating overlay or geometry

Reconcile the owner-run debug-game observation with its exported events and card photo; retain separate evidence gates for identities/upgrades, scaled geometry and vendor overlay.

### Scope
- In: Read-only captured-event comparison and pinned-source geometry/login-gate tracing; current README/verification/runbook/architecture status and remaining gaps.
- Out: New signing/launches, network or account changes, bypassing vendor login gates, treating cropped photos or reader output as independent geometry ground truth.

### Action items
- [x] Verify ordered bootstrap/ready/detection/attach/connect/reward evidence and compare photo names, visible upgrade status and ordering with captured IDs.
- [x] Trace native coordinates and overlay rendering/account gates; record lost scale fields and avoid a tautological compare-reward pass.
- [x] Record successful test-account install/menu confirmation, successful real reward traversal, owner's corrected no-overlay observation, offline-data/settings errors and exact remaining limitations.
- [x] Update canonical status/verification/runbook/architecture, run documentation hygiene/whitespace, commit/push. No tests need changing for this evidence-only slice; existing98 behavior tests remain applicable and do not prove native overlay compatibility.

### Open questions
- None for evidence reconciliation. Future scale-capture instrumentation needs a fresh companion proposal before signing; any network/account experiment needs a separately reviewed plan. Neither is executed here.

Result: read-only event/photo comparison verifies HAZE0/RICOCHET0/INFINITE_BLADES0 and ordering after the complete native event chain. Pinned-source review identifies GlobalUi-normalized raw hitboxes, separate scale fields omitted by our capture, and vendor account gating with silent empty unauthenticated UI. Owner corrected earlier overlay selection: none was noticed on the game screen. Public-data cache and settings-property errors limit broader behavior. Updated current README/table and focused docs; no code, test, signature, account or network change in this slice. All98 existing behavior tests remain applicable. Full geometry/overlay acceptance remains incomplete.

## Controlled manual sign-in, public-data gateway and scale-complete capture

Prepare the vendor OAuth path and required public data behind a default-deny local gateway, retaining the companion's outer remote-network denial and genuine vendor account gates.

### Scope
- In: Original loopback gateway restricted to reviewed HTTPS method/path/body shapes; manual browser OAuth PKCE/callback with memory-only keytar; disable unrelated MTGA upload-token bootstrap and all run/history uploads/telemetry producers; allow account/token/franchise/account/features and public JSON/commentary/tier-list reads; record scale fields and compare rendered hitbox dimensions; bounded private controlled-session launcher and sanitized exports; fresh companion/signing proposal.
- Out: Live sign-in or remote gateway traffic now, automatic browser launch/Terms/OS prompts, bypassing login, network permissions in the app itself, gameplay-context stats/predictions, run history/upload traffic, artwork CDNs, global Keychain/protocol/Steam changes or additional game signing. Browser website traffic is outside companion gateway confinement.

### Action items
- [x] Implement/test a capability-protected loopback gateway with exact HTTPS route/method/body allowlist, no redirects/cookies, public credential stripping, bounded I/O and route-only counters; use fake upstreams in tests.
- [x] Implement/test a controlled Node-fetch adapter and manual authorization URL handoff preserving PKCE/state/callback. Keep raw logs/URLs/tokens private and use only structured sanitized exports; retain default offline behavior.
- [x] Patch exact vendor auth/upload/telemetry seams for controlled mode without faking OAuth/account success. Enumerate only in-memory credentials for the exact service and block all upload-token/claims/run-history/stats routes.
- [x] Retain native scaleX/scaleY in reward capture and require scale evidence for independent rendered-hitbox comparison; preserve legacy raw comparisons as explicitly incomplete. Add meaningful executable JS and geometry tests.
- [x] Add bounded controlled launcher (maximum300 seconds, manual sign-in; optional exact verified debug-game target) with gateway lifetime cleanup and unchanged outer policy. Prepare a test-account script supporting a login-only probe and later reward observation; no raw authenticated log export.
- [x] Prepare fresh copy08 from the pinned vendor source and verify exact entry/native differences, syntax and outer-only original-entitlement signing proposal without signing/launching. Keep current approved game and copy07 intact.
- [x] Update docs/Controlled-Access-Plan.md, README, SECURITY, architecture, runbook and verification with exact permitted disclosures, vendor companion:full-access OAuth consent scope, browser limits, settings/overlay uncertainty and reviewable next command. Run focused/full tests, synthetic local gateway probes, hygiene/syntax and commit/push.

### Open questions
- None for preparation. Actual controlled network/auth execution and fresh-copy signing require approval of the concrete resulting proposal. The user creates/logs into the account manually. The existing settings-reader property error remains an independent overlay prerequisite, not resolved by sign-in alone.

Discovery: vendor OAuth uses accounts.untapped.gg/authorize with PKCE/state and localhost ports17791–17799. Token/account and STS2 exchange/account/features are required; current offline credential branch and findCredentials-empty shim block real account use. authSuccessCallback also attempts unrelated MTGA upload-token acquisition, which must be omitted narrowly to avoid removing a legitimate account. Node-fetch is the main data/auth path; Electron image requests remain separately blocked. Public data and tier/commentary GETs are distinct from gameplay-context stats POSTs. Existing shared raw-log exporter is unsafe after login and will not be reused. Existing98 tests cover current behavior only; new synthetic tests will verify the new boundaries without live credentials/vendor execution.

Implementation checkpoint: controlled gateway/Node adapter/manual OAuth handoff, memory-only credential enumeration, exact auth/upload/telemetry guards, bounded supervisor/sanitized export and scale capture/comparison are implemented. All123 tests pass (including fake local upstreams; no real vendor network). An original inert client reached a fake-upstream gateway under the unchanged outer policy and public credentials were stripped. Copy08 is prepared unsigned, ASAR1c343975300061b01917f5258d9f03089c0bb7ed9e21471e9560f055eeb02720; exactly three packed entries changed, all syntax valid, other138 files/symlinks match source. Signing and controlled-access proposals exist privately; no account/network/vendor execution. Added safe fixed-category settings/cache error booleans to avoid exporting authenticated raw logs. Final docs/hygiene/save remain.

Completion of preparation: added the focused controlled-access review with exact routes/body disclosures, manual browser/PKCE/full-access consent scope, private-log/export limitations and source/fixture evidence. Updated README, SECURITY, architecture, runbook and verification. The source image is detached. All123 tests and synthetic unchanged-policy gateway probe pass; no real requests/signing/vendor execution occurred. Current live copy07/game/scripts remain untouched; copy08 signing and first bounded controlled run await reviewable exact approval. Full UI/geometry/native settings compatibility is not claimed.

Independent boundary review found two concrete follow-ups before final save: freeze gateway/adapter hashes in prepared metadata and reject drift before activation/staging; drain or cancel in-flight upstream work before final gateway counters/export. Implement these within the existing scope, add regressions and refresh copy08's still-unapproved manifest/access proposal after final hashes settle. No new permission or live test is needed for these original-code fixes.

Review follow-up: capture a controlled child exit seen by poll between wait timeouts, so authentication cannot mask a later crash/signal. Added regression preserving exit-5 and nonzero CLI result. Controlled exports now require gateway.cleanup_complete and snapshot route counters only after shutdown/drain. No runtime claim is made if cleanup fails.

Final boundary fixes are implemented: prepared metadata pins gateway/adapter hashes, changed code is refused before activation/staging, gateway handlers drain before final counters and cleanup failure prevents a clean export, and poll-observed child crashes remain nonzero failures. The still-unapproved unsigned copy08 metadata is refreshed to the final helper hashes; no ASAR/native/signature change is involved. Final tests include126 cases.

## Approved copy08 signing and controlled sign-in staging

The owner approved copy08's outer-only signing and first controlled manual sign-in probe: at most300 seconds, ending within45 seconds after genuine authentication. Retain the original five companion entitlements, Hardened Runtime, unchanged outer confinement and reviewed gateway routes. The owner handles Terms, browser sign-in and consent manually in the standard sts2test account.

### Scope
- In: Sign only the prepared copy08 outer bundle; verify signature, entitlements, pinned payloads and helper hashes; stage a profile-free signed archive and current original harness sources; provide the owner-run login-only command.
- Out: New game signing/launch, automated sign-in/Terms/OS prompts, expanded gateway routes, normal-profile access, private-log exports or a claim of working overlay.

### Action items
- [x] Checkpoint this resolved approval before signing the exact prepared copy08 (`4b9b426`).
- [x] Apply the approved outer signature and verify the receipt, native payload pins and original entitlements/Runtime.
- [x] Create and inspect companion08.tar with only app/manifest/signing receipt, preserving file modes; stage its checksum, original helpers and controlled_sign_in.sh with byte parity.
- [x] Update the controlled-access plan and runbook with staged state and verify repository/shell/archive hygiene. Save these results through save-branch. Existing126 tests cover unchanged executable behavior; no test changes are needed for signing, transfer staging and evidence-only documentation.
- [x] Have the owner run the bounded login-only probe in sts2test and review only its sanitized Diagnostic file. The first probe completed with upstream token HTTP403 and no authenticated event; see the diagnosis below.

### Open questions
- None. Approval is explicit; the first live probe requires the owner's manual interaction in UID502 and will not be launched from the assistant's UID501 session.

Staging result: copy08 is signed outer-only and verified with original entitlements/Runtime, signed executable5cc4476cf26ea005a0d4d69021dc9b70a6c7cf939fe9a7e348eb402aed8f3383. The333-entry archive d8b847b8291c6a9f2da72246eabd810c3a52f2e8467681e5ff0c38b0212a85db matches all source entry types/modes/content/links, and a fresh exact-mode extraction passes native signature/payload and helper-policy verification. Current17 original harness sources and controlled launcher are staged with byte parity; checksum, shell/Node syntax, documentation links, repository hygiene and whitespace pass. No vendor process or live request ran. Owner-run authentication and the sanitized result remain pending; the prior126-test suite is unchanged.

## Classify the first controlled token HTTP403 privately

Read only bounded saved authentication-error text inside the owner's private test session and export fixed categories, so the failed token exchange can be diagnosed without copying tokens, URLs, account fields or raw logs.

### Scope
- In: An original read-only auth-error classifier and standard-test-account wrapper; bounded no-symlink owned-file reads; synthetic privacy/path regressions; current controlled-access/runbook/verification evidence.
- Out: Another live request/sign-in, gateway/adapter/ASAR/signature changes, extra routes, copying raw errors or account/token material, and any claim of the HTTP403's cause before the private classifier result is available.

### Action items
- [x] Replay the sanitized first result: one oauth_token HTTP403, no denied route, no authenticated event, clean gateway drain and companion exit0. This proves the request passed local validation; it does not distinguish a vendor OAuth response from an upstream access/security response.
- [x] Checkpoint this resolved plan before implementation (`e3ac1a5`).
- [x] Add fixed-category classification of only bounded token-grant error bodies and original OAuth milestones, with no unrecognized output strings. Keep all raw input private.
- [x] Add an owner-run wrapper restricted to the existing owned private controlled-attempt namespace; do not execute the app or make network requests.
- [x] Add synthetic tests for challenge/HTML/OAuth markers, ignored unrelated text, secret exclusion, bounds, ownership/link/path rejection and generic CLI failures. Run focused/full tests, shell syntax and repository checks.
- [x] Update Controlled-Access-Plan.md, Test-Account-Runbook.md, Verification.md, README and SECURITY.md; stage the original classifier/wrapper with parity and save through save-branch. Give the owner the read-only command.

### Open questions
- None for this diagnostic implementation. The saved private error must be classified by UID502 before choosing a transport or vendor-authentication fix. No new live probe is part of this slice.

Evidence: /private/tmp/sts2test-controlled.7a7o1dnx.json records bootstrap, ready and manual-sign-in-ready, followed by oauth_token403 once. No account/public-data route was reached. Settings/cache false flags in this login-only run do not prove game-settings or public-data compatibility. The browser and companion displayed authentication failure. Ranked diagnostic branches are an upstream HTML/security rejection, a structured OAuth protocol rejection, or another unclassified403; the local allowlist-rejection hypothesis is contradicted by the route counter. The next read-only probe distinguishes these branches without guessing the cause.

Implementation result: the saved-error classifier and standard-account wrapper are staged with exact byte parity. Seven focused tests and the complete133-test suite pass; shell syntax, staged import/help, helper-policy hash binding, documentation links/hygiene and whitespace pass. Source logs are read-only; no network/vendor process, signed-payload change or gateway/adapter change occurred. The owner must run the saved-error command in UID502 and provide only its sanitized Diagnostic file path before the upstream403 can be explained or a concrete fix selected.

## Preserve the original companion User-Agent at the gateway

Restore the pinned original client's HTTP User-Agent in the gateway, then prepare a reviewed helper revision around byte-identical signed copy08 payload for a manual bounded retry.

### Scope
- In: One fixed outbound header matching the original node-fetch library; an inert HTTP regression; an explicit revised gateway hash/proposal and profile-free companion08b transfer; current runbook/access/security/verification docs.
- Out: Browser impersonation, challenge handling, route/body/credential expansion, changed OAuth/PKCE checks, a new app signature/ASAR, game/profile changes, or an automatic live sign-in retry.

### Action items
- [x] Read saved-error classification: token error and callback failure, no recognized JSON OAuth/HTML/challenge/provider markers. Inspect pinned original node-fetch defaults and stdlib transport.
- [x] Compare exactly two credential-free GETs to the existing reviewed account endpoint, changing only User-Agent: current default403 text/plain, original companion header401 JSON with the standard missing-credentials message. Record only fixed metadata, not raw response content. This isolates a header-dependent transport rejection but does not yet prove a successful token exchange.
- [ ] Checkpoint this resolved plan; add an inert on-wire HTTP regression and demonstrate failure before the fix.
- [ ] Set only the fixed original User-Agent inside the gateway transport; keep caller-supplied User-Agent disallowed and expose the fixed value in the review proposal. Run focused and full synthetic suites.
- [ ] Create revision08b with byte-identical signed app/receipt, revised gateway hash and explicit proposal; verify signature/payload/tree equality and exact-mode profile-free archive extraction. Stage the current original helpers and revised default launcher with parity; preserve old archives.
- [ ] Update README, SECURITY.md, Controlled-Access-Plan.md, Test-Account-Runbook.md and Verification.md with measured evidence, reviewable header-only change and retry limits; run syntax/hygiene, checkpoint and push.
- [ ] Have the owner review and initiate the next bounded manual login-only attempt in UID502. Do not claim authentication success from an unauthenticated401 response.

### Open questions
- None for implementation. The owner-run revised sign-in attempt remains a distinct runtime step. Its result is required to establish whether the token failure is resolved.

Discovery: the original packed node_modules/node-fetch/lib/index.js sets User-Agent to node-fetch/1.0 (+https://github.com/bitinn/node-fetch). The gateway's urllib transport instead supplies Python's default when no header is set. The two-request comparison used no tokens/cookies/body/query, normal TLS verification, no redirects, and no browser/app execution. A fixed original-client header preserves integration behavior; no arbitrary client/header or protective-check bypass is added. The signed app need not be modified: only separately reviewed manifest/helper metadata changes, retaining policy-drift checks rather than silently updating the old manifest.
