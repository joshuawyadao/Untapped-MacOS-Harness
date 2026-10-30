# Plan

Build a reversible, version-pinned native macOS diagnostic harness around Untapped's existing STS2 reader and overlay, progressing toward one verified card-reward screen without altering the installed game or saves.

## Scope
- In: Python standard-library CLI, exact archive verification, guarded STS2 and startup-isolation patches on a disposable companion copy, offline startup diagnostics, synthetic regression tests, and separate evidence for startup, detection, attachment, state reading, and overlay display.
- Out: Vendor redistribution, Windows/CrossOver, replacement advice engines, global protection changes, automatic terms acceptance, account login/uploads, game launch or save migration, and signing/entitlement changes without specific approval.

## Action items
- [x] Read the handoff, pinned inspection record, README, CONTRIBUTING, SECURITY, governance, CI, and repository checks; reproduce static archive findings. No application tests or harness framework exist yet.
- [x] Create `codex/native-sts2-poc` and checkpoint this resolved plan before implementation.
- [ ] Implement read-only inspection and fail-closed archive patching with original hashes, exact-match guards, integrity metadata, native binary/fuse observations, and copy-only preparation.
- [ ] Add an isolated offline launcher with fresh settings/logs, memory-only credential shim, disabled updates/telemetry/login-item/protocol registration, and no real home/save access; preserve terms acceptance as a user action.
- [ ] Capture only bounded diagnostic events needed for window detection, reader connection, and reward card IDs/upgrade levels/positions; add a strict comparison command against a manually transcribed real reward screen.
- [ ] Add synthetic tests for malformed/changed archives, narrow patches, copy/source safety, launch isolation, and reward mismatches; run `python3 -m unittest discover -s tests -v`, Node syntax checks, repository hygiene, and `git diff --check`. Extend `CI Verify` for portable behavior tests; vendor code never runs in CI.
- [ ] Attempt preparation and bounded offline startup on the pinned local artifact when safe; stop at any concrete signing/security/terms gate and record each unverified milestone. Never infer reward success from a visible UI.
- [ ] Update README, CONTRIBUTING, governance, and focused architecture/verification docs with ownership, isolation limits, rollback, actual results, and the explicit game-profile strategy needed before gameplay.
- [ ] Review staged files for vendor/private data, checkpoint coherent slices, and push this feature branch through save-branch. Do not open or merge a PR.

## Open questions
- None for implementation. Runtime approval gates are explicit constraints: leave terms untouched and request separate approval for any concrete signing or debugging-entitlement change if evidence shows one is needed.

## Discovery notes

- Pinned companion: `3.12.3-latest`; ASAR SHA-256 `ca3a2e6a6f728b2d635abfc70a5434d4107438b8d801a650357989e8442d798c`.
- Both Electron slices have fuse wire `10110001`: embedded ASAR validation and ASAR-only loading are disabled in this artifact. The Info.plist header hash exists; changing sealed resources still invalidates the vendor bundle seal. No signing workaround is authorized by this plan.
- Existing `UC_TEST_SANDBOX_DIR`, `UC_TEST_SANDBOX_ID`, and `UC_SKIP_UPDATE_CHECKS` hooks help, but do not alone isolate Keychain, telemetry, protocol handlers, or login items.
- No gameplay will be started automatically. A copied game does not isolate Steam Cloud or saves. The first runtime attempt can reach only startup/terms without a separately established gameplay/profile strategy.
- New original harness behavior warrants durable architecture/verification docs and synthetic tests; real captures and vendor files remain outside Git.
