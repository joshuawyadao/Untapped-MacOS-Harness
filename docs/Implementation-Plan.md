# Plan

Trace and repair missing starting-relic tier badges in a separate worktree, preserving the current PR branch and existing Steam, signing and network boundaries.

## Scope
- In: Native starting-choice layout, current tier-list state, renderer visibility/geometry, a narrow verified fix, regression tests and isolated companion validation.
- Out: Changes to the existing PR branch or its preparation workflow, PR creation/merge, statistics API access, game/save mutations, fabricated tiers and automatic login.

## Action items
- [x] Create codex/sts2-starting-relic-badges from44c014c in a separate managed worktree; leave the original checkout unchanged.
- [x] Checkpoint this plan and trace native choice IDs/geometry through IPC, tier merging and renderer gates.
- [x] Add bounded public-choice diagnostics for native geometry, tier coverage, renderer gates and DOM/window measurements; a failing regression awaits a proven cause.
- [ ] Implement the smallest compatibility fix, preserving login/Steam identity guards and all network restrictions.
- [ ] Test missing/invalid geometry, tier coverage and unrelated reward paths, then run the full harness suite and repository checks.
- [ ] Validate patched bundle syntax and payload changes; stage any runtime update separately without disturbing PR preparation or the game.
- [ ] Update architecture/verification and rollout docs, save/push only the focused branch, and record live versus replay evidence explicitly.

## Open questions
- None. The current PR continues independently; this branch initially depends on44c014c and can be rebased after that PR merges.
