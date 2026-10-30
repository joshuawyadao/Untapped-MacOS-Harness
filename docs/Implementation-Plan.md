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
- [ ] Demonstrate one correctly detected real card-reward screen and visually check the existing overlay. Blocked on manual Terms review/acceptance and an agreed gameplay/profile strategy after protected startup reached Terms in logs; no compatibility success is claimed.
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
