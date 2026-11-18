# Plan

Make the macOS harness report a confirmed Slay the Spire 2 process crash even when inventory loses the game before its exit status is available.

## Scope

- In: Live exit classification, private launcher summaries, desktop and CLI messaging, and the installed launcher rebuild.
- Out: Game crash prevention, game or companion changes, and live gameplay reproduction.

## Action items

- [ ] Recreate the reported mismatch with synthetic game inventory and child exit status in the existing main-launcher tests.
- [ ] Check the supervised child's exit status before reporting a guard conflict and reconcile a crash confirmed during cleanup.
- [ ] Show a fixed game-crash message in the desktop worker and CLI, and cover it through their normal entry points.
- [ ] Verify normal exit, live conflicts, and inventory timeout behavior alongside crashes. Run the full suite, native CI smoke tests, and repository checks.
- [ ] Update the desktop guide, main-account runbook, architecture notes, and verification record.
- [ ] Rebuild and verify the signed desktop launcher, preserve the prior bundle for rollback, and update the installed launcher when idle.
- [ ] Commit and push the focused branch.

## Open questions

- None.
