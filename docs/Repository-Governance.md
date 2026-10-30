# Repository governance

## Purpose and current scope

Untapped MacOS Harness aims to make Untapped.gg work with Slay the Spire 2 on macOS. The repository is public for portfolio visibility and collaboration. It now contains an original diagnostic CLI and synthetic tests, but no verified end-to-end compatibility or installable release. See [architecture](Harness-Architecture.md) and [verification](Verification.md) for the actual evidence.

Original project work uses the [MIT License](../LICENSE). Third-party software, assets, and trademarks remain subject to their owners' terms.

## Change workflow

```text
feature branch → pull request → CI Verify + review → squash merge → main
```

The active [Protect main ruleset](https://github.com/joshuawyadao/Untapped-MacOS-Harness/rules/26240959) applies to `main` and the default branch:

| Control | Configuration |
| --- | --- |
| Pull requests | Required for every change |
| Required check | `CI Verify`, bound to the GitHub Actions app |
| Base branch | Must be up to date before merge |
| Review discussions | Must be resolved |
| Human approvals | Zero required during solo maintenance |
| Code owner | `@joshuawyadao`; owner approval is optional |
| Merge method | Squash only; linear history required |
| Force pushes and branch deletion | Blocked |
| Bypass actors | None, including administrators |
| Merged feature branches | Deleted automatically |

Zero required human approvals lets the owner merge their own PR after reviewing the diff and passing checks. When a second regular maintainer joins, consider requiring one approval and code-owner review. The owner can edit repository rules as an administrator, so no repository policy can prevent an authorized administrator from changing the policy itself.

An empty root commit initialized `main` before these controls were enabled, because GitHub needs a base commit for PRs. All project files are introduced through the setup PR.

## Local checks

```sh
git config --local core.hooksPath .githooks
python3 -m unittest discover -s tests -v
node --check harness/bootstrap.cjs
python3 scripts/check_repository.py
git diff --check
```

The hook blocks updates and deletions targeting `refs/heads/main`, including explicit refspecs. It is a local convenience; GitHub rules enforce protection for every clone independently.

`scripts/check_repository.py` checks tracked files for common sensitive paths, private-key markers, files larger than 5 MiB, symlinks, and broken simple inline relative Markdown file links. Stage new files before running it. The link check does not validate remote URLs, headings, reference-style links, or arbitrary Markdown syntax. It does not replace secret scanning or manual review.

The required [CI workflow](../.github/workflows/ci.yml) runs portable Python and stubbed Node bootstrap tests, Node syntax, repository checks, committed whitespace checks, and hook syntax checks on all PRs targeting `main`, on pushes to `main`, and on manual dispatch. It uses a pinned checkout commit, read-only contents permission, no persisted checkout credentials, and a five-minute timeout. There are no path filters that would leave documentation PRs waiting for a skipped required check. Ubuntu can test original harness behavior but cannot prove macOS companion startup or native game integration; retain `CI Verify` as the stable required result if adding macOS jobs.

## GitHub security controls

- Secret scanning and push protection are enabled for supported secret patterns.
- Dependabot alerts and automated security fixes are enabled. Weekly [Dependabot updates](../.github/dependabot.yml) cover GitHub Actions; add application ecosystems when dependency manifests exist.
- Private vulnerability reporting is enabled; see [SECURITY.md](../SECURITY.md).
- Actions tokens default to read-only, and Actions cannot approve PRs.
- Fork PR workflow runs require approval for all external contributors. Inspect proposed workflow changes before approving execution.
- Code scanning and application dependency checks should be configured once supported application code and dependency manifests exist.

## Maintainer operations

The [ruleset definition](../.github/main-ruleset.json) records the intended GitHub policy. Committing changes to it does not apply settings automatically. Review policy changes in a PR, then have an administrator update the existing ruleset through Settings or the API; do not create duplicate rulesets.

Inspect effective policy and security state with an authenticated GitHub CLI:

```sh
gh api repos/joshuawyadao/Untapped-MacOS-Harness/rules/branches/main
gh api repos/joshuawyadao/Untapped-MacOS-Harness/rulesets/26240959
gh api repos/joshuawyadao/Untapped-MacOS-Harness --jq '.security_and_analysis'
gh api repos/joshuawyadao/Untapped-MacOS-Harness/actions/permissions/workflow
```

If CI fails, fix the cause on the feature branch and rerun it. If the branch falls behind, update it from `origin/main`, resolve conflicts, and wait for fresh checks. Avoid weakening protection to get a change through.

Before presenting the harness as working on a resume, demonstrate startup, game detection, reader attachment, a correctly matched real reward screen, overlay behavior, and a reproducible installation path. The current [verification record](Verification.md) does not support a working-compatibility claim. Keep any demonstration free of personal data and proprietary redistribution.

## References

- [GitHub ruleset behavior](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)
- [GitHub repository security settings](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-security-and-analysis-settings-for-your-repository)
- [GitHub Actions permissions API](https://docs.github.com/en/rest/actions/permissions)
