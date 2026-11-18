# Plan

Install one everyday macOS launcher that combines the native live process inventory with confirmed game crash reporting.

## Scope

- In: Combine the launcher changes from `cd83496` and `adfe28a`, verify their interaction, save the combined branch, and replace the everyday signed launcher with a retained rollback copy.
- Out: Overlay performance changes, another gameplay benchmark, Steam or game modifications, and a pull request.

## Action items

- [x] Inspect both revisions, their launcher and retry tests, and the architecture, desktop launcher, migration and verification docs.
- [x] Checkpoint this plan on `codex/combined-launcher` (`4968df3`) before integrating either change.
- [x] Preserve native inventory, target validation and the two-second retry contract while incorporating confirmed and late game-crash reporting in the desktop and terminal launchers. All 59 focused guard, retry, diagnostic and desktop tests passed.
- [x] Verify the integrated guard and reporting with focused synthetic tests, all 378 tests, and the native launcher build and signature checks.
- [x] Update the launcher, architecture, migration and verification docs with the combined behavior and rollout evidence.
- [x] Build the signed launcher from `db0eff9` and replace the idle everyday app under the session lock after normal game and Steam closure. Verify all 43 installed runtime files, the helper pin, and the preserved signed rollback app.
- [x] Verify the installed app opens ready and record the combined rollout on the feature branch.

## Open questions

- None.
