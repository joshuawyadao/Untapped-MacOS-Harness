# Plan

Reduce CPU overhead during gameplay by replacing repeated full-system `ps` scans with a persistent native macOS inventory helper and measuring the change at the live guard's scan cadence.

## Scope

- In: Main-account live process inventory, equivalent candidate and guard decisions for actual game and Steam processes, timeout and retry behavior, portable and macOS tests, a repeatable CPU benchmark, and a saved feature branch.
- Out: Installing the launcher, running gameplay, changing Steam or save data, and modifying the companion or its signing and permissions.

## Action items

- [x] Inspect the live loop, process candidate parser, existing retry tests, launcher packaging, `Desktop-Launcher.md`, `Harness-Architecture.md`, and `Verification.md`.
- [ ] Checkpoint this plan on `codex/native-live-process-inventory`.
- [ ] Add an unprivileged native worker that scans fresh process metadata, preserves local command matching, observes other users' executable identities, and requests a legacy scan when a foreign identity cannot be resolved.
- [ ] Connect the worker to the live guard with a two-second deadline, clean restart after a timeout, and the existing identity, process-group and retry decisions. Keep the legacy pre-launch checks.
- [ ] Add focused coverage for native candidate parity, ownership and duplicate rejection, timeout restart, response failures, cleanup, and the desktop/CLI live call path.
- [ ] Benchmark the legacy and new inventories on this Mac, including the worker's CPU, and record methodology and limits in `Verification.md`.
- [ ] Update `Desktop-Launcher.md` and `Harness-Architecture.md`, run targeted and full tests plus native compilation, and commit and push the feature branch.

## Open questions

- None.
