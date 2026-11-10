# Plan

Fix the STS2 settings-page crash caused by incomplete tier-list metadata, preserving offline UI assets and all-character selections.

## Scope
- In: Reproduce the actual bundled tier comparator exception; guard pending metadata with a visible loading label; regression tests using the real renderer boundary and synthetic entries; versioned companion repair installation, native validation, docs and branch save.
- Out: Altering the live game or Steam progress, expanding API/network permissions, inventing ratings, changing selected authors or automatically signing in.

## Action items
- [x] Confirm the live sanitized TypeError and trace the native comparator and asynchronous metadata-refresh behavior.
- [ ] Checkpoint the plan and add a failing regression for incomplete tier-list sorting/rendering.
- [ ] Patch the guarded tier-list renderer to sort missing names safely and label pending metadata, then build a separately signed repair revision retaining the previous UI update.
- [ ] Verify actual bundled renderer execution against incomplete fixtures, run focused/full tests and native signature/payload checks, and install the revision for the next companion session.
- [ ] Update verification/migration docs with the regression and limits, save/push, and give exact restart instructions while leaving the active game owner-controlled.

## Open questions
- None. This is a regression fix within the authorized companion UI repair and signing scope.
