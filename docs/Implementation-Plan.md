# Plan

Install one everyday macOS launcher that combines the native live process inventory with confirmed game crash reporting.

## Scope

- In: Combine the launcher changes from `cd83496` and `adfe28a`, verify their interaction, save the combined branch, and replace the everyday signed launcher with a retained rollback copy.
- Out: Overlay performance changes, another gameplay benchmark, Steam or game modifications, and a pull request.

## Action items

- [x] Inspect both revisions, their launcher and retry tests, and the architecture, desktop launcher, migration and verification docs.
- [ ] Checkpoint this plan on `codex/combined-launcher` before integrating either change.
- [ ] Preserve native inventory, target validation and the two-second retry contract while incorporating confirmed and late game-crash reporting in the desktop and terminal launchers.
- [ ] Verify the integrated guard and reporting with focused synthetic tests, the full suite, and the native launcher build and signature checks.
- [ ] Update the launcher, architecture, migration and verification docs with the combined behavior and rollout evidence.
- [ ] Build a signed launcher from the saved source, verify the bundled runtime and helper pin, and replace the idle everyday app under the session lock after normal game closure and Steam Cloud synchronization. Preserve the exact previous app for rollback.
- [ ] Verify the installed app opens ready and save the combined feature branch.

## Open questions

- None.
