# Plan

Prepare migration toward the owner's existing main-account and Steam progress by adding a read-only readiness check and recording an explicit save/Cloud strategy before activating a new launcher.

## Scope
- In: The owner's confirmed existing-progress target; fixed-path, same-account directory metadata inspection; pinned installed-game verification; privacy-safe readiness output; copy09 visible-overlay/settings evidence; a staged migration document and synthetic tests.
- Out: Main-account game/companion launch, signing or entitlement changes, save reads/copies/writes/restores, Steam/Cloud configuration changes, persistent credentials, longer live sessions, broader network routes or claims of complete compatibility.

## Action items
- [x] Map current account/target guards, test coverage and architecture/security/runbook docs. Confirm copy09's sanitized report matches the photo: native settings and reward read, overlay show, no old property error; actual tier labels remain unresolved.
- [x] Inspect pinned game metadata/static save contracts and current Valve documentation. Confirm app copying does not isolate the configured custom user-data directory; retain Cloud synchronization and Steam restart behavior as separate unresolved runtime checks.
- [ ] Checkpoint this resolved plan before code changes. Keep current test-account execution guards intact.
- [ ] Add `harness/main_account.py` with a read-only CLI deriving the actual home from pwd, inspecting only the fixed installed game and custom data root, bounding no-follow directory scans and rejecting ambiguous/inaccessible/redirected inputs. Export fixed enums/booleans/counts only; never save contents, Steam IDs, paths, names, timestamps or hashes of saves.
- [ ] Add synthetic tests for pinned game metadata, path/owner/link failures, bounded scans, missing roots, privacy/content-open traps and no launch/network/signing/mutation. Run focused tests and the full portable suite.
- [ ] Run the readiness check in the normal account without touching saves or private Steam/companion contents; record only its sanitized result. An absent or multiple Steam namespace is an unresolved selection condition, never permission to pick an account automatically.
- [ ] Update README, SECURITY, architecture, verification, runbook and `docs/Main-Account-Migration.md` with confirmed evidence, exact read-only command, proposed migration phases and inactive boundaries. Validate links, shell/JS syntax, whitespace and source hygiene.
- [ ] Review the new boundary, checkpoint and push through save-branch. Leave main-account launch disabled; the later launch proposal must identify exact copied apps, entitlements, save-write/backup behavior, Steam/Cloud participation, credentials, session and exit policy before any activation approval.

## Open questions
- None for this read-only milestone. The owner explicitly wants existing main-account/Steam progress eventually. Actual Steam/Cloud readiness and the later exact launch policy are technical follow-up gates, not assumptions or a request to repeat that preference.
