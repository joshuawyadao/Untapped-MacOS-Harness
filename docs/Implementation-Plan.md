# Plan

Prepare migration toward the owner's existing main-account and Steam progress by adding a read-only readiness check and recording an explicit save/Cloud strategy before activating a new launcher.

## Scope
- In: The owner's confirmed existing-progress target; fixed-path, same-account directory metadata inspection; pinned installed-game verification; privacy-safe readiness output; copy09 visible-overlay/settings evidence; a staged migration document and synthetic tests.
- Out: Main-account game/companion launch, signing or entitlement changes, save reads/copies/writes/restores, Steam/Cloud configuration changes, persistent credentials, longer live sessions, broader network routes or claims of complete compatibility.

## Action items
- [x] Map current account/target guards, test coverage and architecture/security/runbook docs. Confirm copy09's sanitized report matches the photo: native settings and reward read, overlay show, no old property error; actual tier labels remain unresolved.
- [x] Inspect pinned game metadata/static save contracts and current Valve documentation. Confirm app copying does not isolate the configured custom user-data directory; retain Cloud synchronization and Steam restart behavior as separate unresolved runtime checks.
- [x] Checkpoint this resolved plan before code changes. Keep current test-account execution guards intact.
- [x] Add `harness/main_account.py` with a read-only CLI deriving the actual home from pwd, inspecting only the fixed installed game and custom data root, bounding no-follow directory scans and rejecting ambiguous/inaccessible/redirected inputs. Export fixed enums/booleans/counts only; never save contents, Steam IDs, paths, names, timestamps or hashes of saves.
- [x] Add synthetic tests for pinned game metadata, path/owner/link failures, bounded scans, missing roots, privacy/content-open traps and no launch/network/signing/mutation. Run focused tests and the full portable suite.
- [x] Run the readiness check in the normal account without touching saves or private Steam/companion contents; record only its sanitized result. An absent or multiple Steam namespace is an unresolved selection condition, never permission to pick an account automatically.
- [x] Update README, SECURITY, architecture, verification, runbook and `docs/Main-Account-Migration.md` with confirmed evidence, exact read-only command, proposed migration phases and inactive boundaries. Validate links, shell/JS syntax, whitespace and source hygiene.
- [x] Review the new boundary, checkpoint and push through save-branch. Leave main-account launch disabled; the later launch proposal must identify exact copied apps, entitlements, save-write/backup behavior, Steam/Cloud participation, credentials, session and exit policy before any activation approval.

## Open questions
- None for this read-only milestone. The owner explicitly wants existing main-account/Steam progress eventually. Actual Steam/Cloud readiness and the later exact launch policy are technical follow-up gates, not assumptions or a request to repeat that preference.

Implementation evidence: resolved plan checkpoint01452cd precedes code. The read-only normal-account check finds a pinned release/assembly match and one Steam namespace/profile with complete bounded metadata. No saves/config/auth contents were opened, no apps/network/signing launched, no progress copied/written/restored and no Cloud setting changed. Exact no-follow directory descriptor walks and nonblocking regular vendor-file opens handle ancestor redirects and FIFO risks. Eleven focused tests pass; an initial full suite of172 passed before the final three fault/bounds/side-effect tests were added. Final full-suite/hygiene and save-branch completion follow. Updated migration/README/security/architecture/runbook/verification describe actual09 rendering/settings recovery, unresolved ratings and the inactive existing-Steam-progress target. No unrelated file or staged09 runtime artifact is changed.

Final validation: all175 tests pass, including11 new inspector tests. Original bootstrap/store-helper JS and controlled-launcher shell syntax pass; tracked and new-file hygiene, Markdown links and whitespace pass. Read-only review has no remaining blocking finding. The normal-account fixed-field inspection completed without any active operation; existing test-account guards and staged09 payload/policy/signature bytes remain unchanged. This readiness milestone is complete; main-account launcher/backup/Steam-Cloud activation remains explicitly unimplemented and disabled. Save-branch records the final implementation/docs checkpoint after01452cd and pushes the feature branch; no PR or merge is part of this task.
