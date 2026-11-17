# Plan

Support the measured Slay the Spire 2 v0.111.1 build through an immutable verified game-copy update, check the genuine Untapped reader, and install a signed launcher while retaining existing Steam progress and rollback artifacts.

## Scope
- In: New feature branch; exact v0.111.1/cc1f9462 assembly and full-tree pins; explicit build-aware game verification/signing; a separately published main-account game-copy layer; current game/account/progress/companion gates; synthetic regressions; signed launcher staging and guarded replacement; read-only and owner-controlled live compatibility checks.
- Out: Modifying Steam's installed game or saves, restoring progress, changing Steam Cloud settings, weakening version/signature/identity/account checks, expanding companion network access, fabricated ratings, proprietary code redistribution, or merging a PR.

## Action items
- [x] Inspect Desktop-Launcher, Main-Account-Migration, Harness-Architecture, Verification and current launch/debug-copy tests. Reproduce SOURCE_CHANGED: installed v0.111.1/cc1f9462 differs from legacy v0.107.1/59260271. Measure new assembly/tree hashes and both original four-entitlement/ad-hoc/Hardened Runtime contracts.
- [x] Commit this resolved plan before implementation on codex/sts2-v0.111.1-compatibility (`17d5347`).
- [x] Add explicit reviewed-build verification/signing while retaining legacy defaults and receipts; five new build tests plus the legacy game tests pass. Exact new installed source validation passes without modifying it.
- [x] Add an immutable main-account game update with fixed paths, old-binding lineage, last-step receipt publication and exclusive session lock. Seven new synthetic tests cover incomplete/tampered/idempotent states, source/account selection and preservation. Independent read-only review found no blocking defect; interrupted publication intentionally requires recovery.
- [x] Route prepared validation and all pre-launch source/copy rechecks through the selected build, preserving backup-before-Steam, current account/profile checks and immediate mismatch stops. Existing 23 launch tests and four builder tests pass, including selected-copy icon use; update tests prove executable selection and refusal before spawn if selection changes.
- [x] Inspect Untapped's native reader and new managed data contracts without touching credentials; all 368 tests and signed native build pass. Update architecture, migration, launcher and verification docs with exact evidence and limits. Managed contracts look compatible; native engine changes still require live verification.
- [x] Prepare/sign/verify the authorized separate game copy and signed launcher snapshot, then replace the installed launcher under the session lock after confirming Steam/game/worker absence. The owner closed the window; its verified orphan idle frontend (no children) received normal SIGTERM before replacement. All 41 runtime files, native signatures/helper pin and unchanged progress verify; the previous launcher is retained.
- [x] Verify installed runtime/native hashes and owner-controlled startup. Live v0.111.1 inspection confirms exact game/companion processes, reader connection, expected Steam/profile and normal Steam/Cloud-storage flags. The owner confirms aligned starting-choice and current reward badges; a paused combat independently matches two attacks (10 + 7) to 2 Hits/17, with panel/icon visible. The bounded reward stream's exhausted sample cap remains an explicit current-ID measurement limit.
- [x] Record completed validation and installed/rollback artifacts, commit checkpoints and save the feature branch. All 368 local tests and native build/signatures pass. Hosted Ubuntu passes on f84f0e6; the unchanged native-source job remains queued for a macOS runner as of this record. No PR is opened or merged; private/vendor artifacts remain outside Git.

## Open questions
- None. The user explicitly requests the new build, copied-game/launcher update, compatibility testing and preservation of existing Steam progress. Existing account/Cloud confirmations remain owner-controlled operational steps when the updated launcher starts.

## Validation limits
- Live evidence covers the tested starting choices, reward badge rendering/alignment and one matched combat total; it is not exhaustive coverage of every character, screen, modifier, full-screen transition or long session.
- Earlier reward IDs/scales were sampled successfully, but the existing 100-sample diagnostic cap prevents representing them as later card identities. Current reward evidence uses the actual game screenshot, live overlay accessibility tree and owner confirmation.
- Hosted CI run44142488199 tests saved head f84f0e6; final edits are documentation only. The queued hosted macOS job is not a pass. Actual local native compilation/signatures and installed runtime parity already pass; a future PR must obtain its own fresh required checks.
