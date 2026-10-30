# Plan

Prepare Untapped MacOS Harness for public portfolio viewing with protected GitHub collaboration, accurate documentation, and a small verified repository baseline.

## Scope
- In: Connect local Git to the supplied public repository, protect `main`, add public-facing documentation and contribution templates, configure repository checks and dependency updates, and publish a setup PR.
- Out: Harness implementation, invented feature claims, and application build tooling before a stack exists.

## Action items
- [x] Inspect the empty workspace and remote, Git identity, permissions, docs, and tests; none exist yet. Bootstrap an empty `main` so subsequent files can use a PR.
- [x] Checkpoint this plan on `chore/public-repository-setup` before adding project files.
- [x] Configure and verify an active `main` ruleset: PRs, `CI Verify`, current base branch, resolved discussions, linear history, blocked deletion/force pushes, and no bypass actors; retain zero human approvals for solo maintenance.
- [x] Enable squash merging, automatic branch deletion, secret scanning, push protection, private vulnerability reporting, Dependabot alerts/updates, and least-privilege Actions permissions where supported.
- [x] Add README describing the goal of making Untapped.gg work with Slay the Spire 2 on macOS, the owner-selected MIT license, contribution/security guidance, ownership, issue/PR templates, Git ignore/formatting rules, and a local hook that blocks pushes to `main`.
- [x] Add a pinned GitHub Actions workflow named `CI Verify`, a dependency-free repository hygiene check, and GitHub Actions Dependabot updates. No application test files are appropriate before executable harness behavior exists; validate the new checks with positive and negative fixtures.
- [x] Document Git workflow, actual security controls, solo-review tradeoffs, MIT licensing limited to original project code, and future portfolio/build/test milestones in `docs/Repository-Governance.md`.
- [x] Validate tracked-file hygiene, Markdown links, workflow/template YAML, hook behavior, and GitHub API readback. Confirm that no credentials, personal captures, or generated artifacts enter history.
- [ ] Commit and push the setup branch, open a PR, request Codex review, run Brooks review, resolve actionable feedback/CI failures, and report verified status without merging.

## Open questions
- None. The owner confirmed the compatibility goal and selected MIT licensing. Describe compatibility as a goal until implementation and evidence exist.

## Validation and review ledger

- Local baseline: 19 tracked files passed repository hygiene and relative Markdown link checks; Python compilation, shell syntax, YAML parsing, and staged whitespace checks passed.
- Temporary fixtures: 11 hygiene cases exercised allowed files, environment files, signing files, capture directories, synthetic private-key markers, size limits, links, and symlinks. Five hook cases covered feature pushes, explicit main refspecs, deletion, mixed refs, and empty pushes. Fixtures stayed outside repository history.
- Independent correctness review found that the default combined merge diff could skip PR whitespace errors. CI now fetches two commits and checks first-parent changes; a temporary PR-style merge reproduced the omission and confirmed the corrected command rejects it in a depth-two checkout.
- GitHub readback confirmed the active ruleset with no bypass actors, the required Actions check, squash-only merges, branch cleanup, secret scanning/push protection, Dependabot alerts/automated fixes, private vulnerability reporting, read-only Actions tokens, and approval for external fork workflows.
- Application tests: none added because no harness behavior exists. Repository safety behavior was verified with temporary positive and negative fixtures instead of introducing an application test framework.
- Remaining: publish the setup branch and PR, complete Brooks/Codex review and remote CI, and leave the PR unmerged for the owner.
