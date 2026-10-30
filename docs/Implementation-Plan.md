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
- [ ] Demonstrate one correctly detected real card-reward screen and visually check the existing overlay. Blocked by Gatekeeper rejecting the patched disposable companion and an agreed gameplay/profile strategy; no compatibility success is claimed.
- [x] Prepare a reviewable, opt-in outer-companion ad-hoc signing command and session-bound receipt guard, with synthetic tests. Do not execute signing until the owner explicitly approves the exact per-copy change. Preserve the five original entitlements, Hardened Runtime, nested code, and all game/OS protections.

## Open questions
- None for implementation. Runtime approval gates are explicit constraints: leave terms untouched and request separate approval for any concrete signing or debugging-entitlement change if evidence shows one is needed.

## Discovery notes

- Pinned companion: `3.12.3-latest`; ASAR SHA-256 `ca3a2e6a6f728b2d635abfc70a5434d4107438b8d801a650357989e8442d798c`.
- Both Electron slices have fuse wire `10110001`: embedded ASAR validation and ASAR-only loading are disabled in this artifact. The Info.plist header hash exists; changing sealed resources still invalidates the vendor bundle seal. No signing workaround is authorized by this plan.
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
- The original desktop-observation blocker is resolved; the next runtime action now requires explicit approval of the per-copy signing proposal below. One real card-reward match remains the acceptance milestone.
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
