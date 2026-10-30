# Plan

Prepare Untapped MacOS Harness for public portfolio viewing with protected GitHub collaboration, accurate documentation, and a small verified repository baseline.

## Scope
- In: Connect local Git to the supplied public repository, protect `main`, add public-facing documentation and contribution templates, configure repository checks and dependency updates, and publish a setup PR.
- Out: Harness implementation, invented feature claims, application build tooling before a stack exists, and choosing an open-source license without the owner's direction.

## Action items
- [x] Inspect the empty workspace and remote, Git identity, permissions, docs, and tests; none exist yet. Bootstrap an empty `main` so subsequent files can use a PR.
- [ ] Checkpoint this plan on `chore/public-repository-setup` before adding project files.
- [ ] Configure and verify an active `main` ruleset: PRs, `CI Verify`, current base branch, resolved discussions, linear history, blocked deletion/force pushes, and no bypass actors; retain zero human approvals for solo maintenance.
- [ ] Enable squash merging, automatic branch deletion, secret scanning, push protection, private vulnerability reporting, Dependabot alerts/updates, and least-privilege Actions permissions where supported.
- [ ] Add README, contribution/security guidance, ownership, issue/PR templates, Git ignore/formatting rules, and a local hook that blocks pushes to `main`.
- [ ] Add a pinned GitHub Actions workflow named `CI Verify`, a dependency-free repository hygiene check, and GitHub Actions Dependabot updates. No application test files are appropriate before executable harness behavior exists; validate the new checks with positive and negative fixtures.
- [ ] Document Git workflow, actual security controls, solo-review tradeoffs, reserved licensing unless directed otherwise, and future portfolio/build/test milestones in `docs/Repository-Governance.md`.
- [ ] Validate tracked-file hygiene, Markdown links, workflow/template YAML, hook behavior, and GitHub API readback. Confirm that no credentials, personal captures, or generated artifacts enter history.
- [ ] Commit and push the setup branch, open a PR, request Codex review, run Brooks review, resolve actionable feedback/CI failures, and report verified status without merging.

## Open questions
- None blocking. Until the owner supplies a project description or license preference, describe the repository as an initial macOS harness scaffold and reserve reuse rights.
