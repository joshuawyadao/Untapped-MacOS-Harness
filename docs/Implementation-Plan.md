# Plan

Repair the attack-summary image placeholder by embedding the five pinned public intent icons and safely upgrading existing offline UI copies for the next normal launch.

## Scope
- In: Fixed intent-image downloads at preparation time, local data-URI replacement, versioned UI update installation/selection, regression tests and documentation.
- Out: Damage calculation changes, live game interruption, save/Steam changes, authentication changes, runtime network expansion and other dynamic artwork.

## Action items
- [x] Trace AttackSummary/AttackIntentIcon and review ui_assets.py, ui_update.py, their tests and UI rollout documentation.
- [ ] Checkpoint this plan before implementation.
- [ ] Add a fixed five-image allowlist and guarded intent URL replacement; support fresh preparation and incremental upgrade from UI version 1.
- [ ] Install UI version 2 alongside the retained version 1 copy and atomically select only a completely verified signed update; preserve rollback and policy bindings.
- [ ] Add regressions for all five images, download/anchor failures, legacy selection, upgrade failure and completed-update selection.
- [ ] Run targeted/full tests, bundle syntax checks, repository checks and a real private-copy preparation with payload/signature verification.
- [ ] Activate the prepared update for the next normal launch without restarting the current game; record live visual validation as pending until a combat encounter.
- [ ] Update migration, architecture and verification docs; save/push the refinement branch.

## Open questions
- None. Existing copied-companion repair/signing authorization applies; the running session remains untouched.
