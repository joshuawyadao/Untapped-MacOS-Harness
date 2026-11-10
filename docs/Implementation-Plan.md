# Plan

Trace the reported missing starting-relic tier badges in a separate worktree, preserving the current PR branch and existing Steam, signing and network boundaries. Live verification confirmed visible named-tier badges without a rendering change; finish with the evidence record rather than a speculative repair.

## Scope
- In: Native starting-choice layout, current tier-list state, renderer visibility/geometry, isolated companion validation and documentation of the verified result. A code fix and regression tests are conditional on a reproduced defect.
- Out: Changes to the existing PR branch or its preparation workflow, PR creation/merge, statistics API access, game/save mutations, fabricated tiers and automatic login.

## Action items
- [x] Create codex/sts2-starting-relic-badges from 44c014c in a separate managed worktree; leave the original checkout unchanged.
- [x] Checkpoint this plan and trace native choice IDs/geometry through IPC, tier merging and renderer gates.
- [x] Add bounded public-choice diagnostics for native geometry, tier coverage, renderer gates and DOM/window measurements.
- [x] Resolve the implementation decision: three correctly sized, visible badge elements and owner-confirmed “Inconsistent” labels establish working named-tier badges. No rendering repair is justified; no application code changes.
- [x] Validate diagnostic bundle syntax, signatures and allowed payload changes in separate temporary copies; retain installed selection and game unchanged.
- [x] Record live evidence and the initial diagnostic selector limitation. No regression tests added or full suite rerun because the final repository change is documentation only; use repository hygiene and diff checks.
- [x] Prepare the focused documentation branch for the final save/push step. Architecture and rollout behavior are unchanged; verification links to the focused evidence. The final save result is reported separately.

## Open questions
- None. The current PR continues independently; this branch initially depends on 44c014c and can be rebased after that PR merges.
