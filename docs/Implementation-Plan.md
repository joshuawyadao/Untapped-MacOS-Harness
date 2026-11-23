# Plan

Keep the overlay through recoverable inventory stalls by detaching timed-out scans, alternating fresh inventory backends during recovery, and allowing a bounded set of retries.

## Scope

- In: Diagnose the November 23 shutdown with retained evidence, harden live inventory and retry handling, add safe fault-stage diagnostics and regressions, and install the tested update after the current session ends.
- Out: Changing startup and isolated-account checks, weakening game or account validation, changing the overlay, and opening a pull request.

## Action items

- [x] Inspect the incident, live inventory, retry and diagnostics tests, and desktop, architecture and verification docs. Reproduce the three-timeout shutdown and show how synchronous worker cleanup can extend the recorded time from 2 seconds to 7.646 seconds. Track the initial OS stall as unresolved unless historical evidence identifies it.
- [x] Checkpoint this plan on `codex/inventory-timeout-recovery` (`a923fed`).
- [x] Add red regressions for a healthy fourth scan, a stalled child reap, and a fresh alternate scan after a timeout.
- [x] Bound worker cleanup and the legacy scan, switch to the alternate scanner during recovery, and retain a fixed timeout stage without process data. Keep the two-second scan deadline and let six consecutive timeouts exhaust recovery with longer delays after the first two retries.
- [x] Verify fresh snapshots, mismatch handling, cancellation, and exhaustion. All 382 tests and native checks passed. Record the initial incident, the separate fixture-triggered stop, the synthetic recovery, and the host rollout in the launcher, architecture and verification docs.
- [x] Build and install the signed launcher from `a9ebedc` after normal game and Steam closure. Verify all 43 runtime files, the helper pin, rollback, and the ready screen. Record the verified rollout on the feature branch.

## Open questions

- None.
