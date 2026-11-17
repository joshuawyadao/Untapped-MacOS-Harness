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
- [ ] Inspect Untapped's native reader and new managed data contracts without touching credentials; run focused/full synthetic tests and native compilation/signatures. Update architecture, migration, launcher and verification docs with exact evidence and limits.
- [ ] Prepare/sign/verify the authorized separate game copy and build a signed launcher snapshot. Replace the installed launcher under the session lock only after verifying no active game/Steam/worker and preserve its rollback bundle.
- [ ] Verify installed runtime/native hashes and owner-visible controls; use the owner's normal Steam/account confirmations to observe reader connection, matching Steam profile, real state and visible overlay on v0.111.1. Never equate synthetic/static checks with live compatibility.
- [ ] Record completed validation, installed artifacts and any concrete compatibility blocker; commit checkpoints and push the feature branch using save-branch. Leave unrelated artifacts and private/vendor payloads outside Git.

## Open questions
- None. The user explicitly requests the new build, copied-game/launcher update, compatibility testing and preservation of existing Steam progress. Existing account/Cloud confirmations remain owner-controlled operational steps when the updated launcher starts.
