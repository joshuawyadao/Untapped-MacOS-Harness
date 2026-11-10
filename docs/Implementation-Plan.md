# Plan

Make main-account CLI exit status reflect safety-stop failures found in PR review, using explicit successful stop reasons and synthetic regressions.

## Scope
- In: Launcher outcome classification, CLI regression tests, migration/verification documentation, Brooks review history, and the observed Ubuntu CI fixture failures.
- Out: Live launches, installed companion changes, process termination changes, saves, Cloud operations, or broader refactoring. The previous tier-list queue milestone is complete and recorded in Verification.md.

## Action items
- [x] Review main_launcher.py, main_companion.py, tests/test_main_launcher.py, Main-Account-Migration.md and Verification.md.
- [x] Checkpoint this plan before implementation.
- [x] Require a known successful stop reason in the CLI alongside authentication, account verification and cleanup.
- [x] Cover target conflict, mismatch, unknown/missing reasons, and supported successful stops using synthetic CLI results.
- [x] Document exit-status semantics and review evidence; record the sampled Brooks review.
- [x] Run launcher regressions and all238 local tests, commit and push the safety-stop correction.
- [x] Correct the game fixture UID and connection-refused errno to match the host without weakening expected behavior.
- [x] Provision the required macOS-style `/private/tmp` test root on the ephemeral Ubuntu runner, preserving namespace validation in production and tests.
- [x] Record CI fixture requirements in CONTRIBUTING.md and validation in Verification.md; run affected/full tests and hygiene checks, commit and push.
- [x] Confirm Ubuntu CI passes after fixture corrections; acknowledge the matching Codex finding after push.
- [x] Preserve the companion exit code before owned-group cleanup and report nonzero or signal exits as PROCESS_EXIT failures, retaining private evidence.
- [x] Add synthetic zero/nonzero/signal exit regressions and a CLI crash outcome case; update migration/verification docs, validate and save.
- [ ] Recheck Codex review, CI and mergeability; leave protected review-thread resolution and final merge to the owner unless explicitly authorized.

## Open questions
- None. Safety-stop failures must return nonzero; normal game/companion exit and the session limit retain existing successful behavior when all other checks pass.
