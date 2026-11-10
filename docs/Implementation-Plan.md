# Plan

Make main-account CLI exit status reflect safety-stop failures found in PR review, using explicit successful stop reasons and synthetic regressions.

## Scope
- In: Launcher outcome classification, CLI regression tests, migration/verification documentation, and Brooks review history.
- Out: Live launches, installed companion changes, process termination changes, saves, Cloud operations, or broader refactoring. The previous tier-list queue milestone is complete and recorded in Verification.md.

## Action items
- [x] Review main_launcher.py, main_companion.py, tests/test_main_launcher.py, Main-Account-Migration.md and Verification.md.
- [x] Checkpoint this plan before implementation.
- [x] Require a known successful stop reason in the CLI alongside authentication, account verification and cleanup.
- [x] Cover target conflict, mismatch, unknown/missing reasons, and supported successful stops using synthetic CLI results.
- [x] Document exit-status semantics and review evidence; record the sampled Brooks review.
- [ ] Run focused and full tests, repository/whitespace/syntax checks, commit and push; recheck Codex review, CI and mergeability.

## Open questions
- None. Safety-stop failures must return nonzero; normal game/companion exit and the session limit retain existing successful behavior when all other checks pass.
