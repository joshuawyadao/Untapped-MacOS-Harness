# Plan

Bring the CI feature branch onto current main while preserving its portable/native enforcement, validate the current launcher sources, and prepare a reviewed merge-ready PR.

## Scope
- In: Merge current main into codex/ci-test-baseline-2026-11-16 without rewriting published history; preserve Ubuntu tests, isolated macOS compilation/signatures/native seam tests, and the unconditional CI Verify aggregate; maintain focused regression tests and CI documentation.
- Out: Product behavior changes, rebuilding installed apps, game/Steam/Keychain operations, repository-rule changes, unrelated CI infrastructure, and merging the resulting PR.

## Action items
- [x] Inspect the three unique CI commits, current main/PR4 contents, workflow, scripts, native seam tests and Desktop-Launcher docs; verify GitHub's always/needs behavior against official documentation. The branch's older remembered-login snapshot must not undo newer supervision or full-screen changes.
- [x] Commit this resolved plan as a local checkpoint before merging or implementing (`90fd34f`).
- [ ] Merge origin/main, resolve any documentation conflict by preserving the current plan plus both branches' operational intent, and prove harness/launcher sources match main byte-for-byte.
- [x] Assess aggregate-job failure/skip/cancel/missing-result coverage and native-build isolation; extend result cases to unset/empty/unknown values and scope required-gate/native assertions to their own jobs. No production defect was found.
- [ ] Run targeted CI regressions, the current full suite, isolated native compile/signature checks, YAML/shell/repository/whitespace checks, and update Desktop-Launcher/Verification CI evidence without changing installed applications.
- [ ] Save/push the updated feature branch and open a draft PR scoped to its CI changes.
- [ ] Run Brooks and Codex reviews, handle actionable feedback, and verify actual portable/macOS/aggregate jobs pass on the final head with the existing required CI Verify context and no merge conflicts.
- [ ] Mark the PR ready, make a final fresh gate check, and leave it unmerged with a concise review/validation ledger and documented limits.

## Open questions
- None. The user explicitly requests updating the named branch and preparing its PR; use a normal merge to preserve shared branch history and existing main protections.
