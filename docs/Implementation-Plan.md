# Plan

Make the macOS harness report a confirmed Slay the Spire 2 process crash even when inventory loses the game before its exit status is available.

## Scope

- In: Live exit classification, private launcher summaries, desktop and CLI messaging, and the installed launcher rebuild.
- Out: Game crash prevention, game or companion changes, and live gameplay reproduction.

## Action items

- [x] Recreate the reported mismatch with synthetic game inventory and child exit status in the existing main-launcher tests.
- [x] Check the supervised child's exit status before reporting a guard conflict and reconcile a crash confirmed during cleanup.
- [x] Show a fixed game-crash message in the desktop worker and CLI, and cover it through their normal entry points.
- [x] Verify normal exit, live conflicts, and inventory timeout behavior alongside crashes. All 372 tests, native signing checks, and repository checks passed.
- [x] Update the desktop guide, main-account runbook, architecture notes, and verification record.
- [x] Rebuild and verify the signed desktop launcher. Replay the saved incident summary through the bundled worker to confirm the new message.
- [x] Save the verified fix on a focused branch.
- [ ] Preserve the prior app for rollback and replace the installed launcher after active gameplay and companion cleanup finish.

## Open questions

- None.
