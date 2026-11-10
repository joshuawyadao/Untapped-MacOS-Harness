# Plan

Fix the STS2 settings-page crash caused by incomplete tier-list metadata, preserving offline UI assets and all-character selections.

## Scope
- In: Reproduce the actual bundled tier comparator exception; supply a truthful temporary display name in fresh profile entries; regression tests using the native comparator boundary and synthetic entries; preserve minimal persisted preferences, docs and branch save.
- Out: Altering the live game or Steam progress, expanding API/network permissions, inventing ratings, changing selected authors or automatically signing in.

## Action items
- [x] Confirm the live sanitized TypeError and trace the native comparator and asynchronous metadata-refresh behavior.
- [x] Checkpoint the plan and add a failing regression for incomplete tier-list sorting/rendering.
- [x] Give fresh-profile tier selections a temporary loading name without adding ratings, author, keyCards or gameVersion; retain native metadata refresh and strip the placeholder on preference harvest.
- [x] Verify actual bundled renderer execution against incomplete fixtures, run focused/full tests and unchanged signed-payload checks, and apply the fix on the next companion session.
- [x] Update verification/migration docs with the regression and limits, save/push, and give exact restart instructions while leaving the active game owner-controlled.

## Open questions
- None. This is a regression fix within the authorized companion UI repair and signing scope.

Result: the exact native comparator reproduces the pre-fix TypeError and passes on fixed synthetic seed output. Temporary display names are fresh-profile-only and preserve genuine refresh; signed assets remain unchanged. Full-suite/save results are recorded in Verification.md. The supervised companion is reopened beside the retained game; manual owner sign-in/settings visual confirmation remains.
