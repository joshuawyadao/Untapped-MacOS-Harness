# Plan

Reduce live inventory fallback work and let short macOS process-table outages recover without weakening the launcher's target and conflict checks.

## Scope

- In: Diagnose the 11:20 Pacific fallback stall, scope fallback to unresolved rows when a native scan completed, extend the bounded retry period, verify the checked process and account behavior, and install the signed build after normal quit.
- Out: Changes to startup and isolated-account inventory, game or companion signing, and overlay features.

## Action items

- [x] Match the live session report, reproduce six-attempt exhaustion with a healthy seventh scan, and compare whole-table with selected-PID macOS process lookups. The historical source of the process lookup stall remains unconfirmed.
- [x] Checkpoint this plan on `codex/scoped-inventory-recovery`.
- [x] Emit unresolved PID and owner rows with the fresh native candidate snapshot. Resolve those rows through per-PID `ps`, require complete owner-matching coverage, and require a fresh whole-table scan when the scoped response is inconclusive or the native snapshot is unavailable.
- [x] Extend transient timeout recovery to 60 seconds after the first timeout. Keep two-second attempt deadlines, bounded backoff, account and exit checks, and verify the tracked game process group during recovery. Keep PID, owner, executable, group and conflict checks on every accepted inventory.
- [x] Add regressions for a long recovered stall, bounded exhaustion, and scoped fallback coverage and timeouts. Run focused, full, native and repository checks with game-name fixtures isolated from live sessions. Record actual evidence and limits in the launcher, architecture and verification docs.
- [x] Build and install the verified launcher once the game and Steam close normally, preserve rollback, and commit and push the branch.

## Open questions

- None.
