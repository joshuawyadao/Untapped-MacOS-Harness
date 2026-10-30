# Contributing

This project aims to make Untapped.gg work with Slay the Spire 2 on macOS. Compatibility research, reproducible bug reports, and focused implementation changes are welcome.

## Local setup

Install Git and Python 3.9 or newer, then clone the repository. Contributors without write access should fork it first.

```sh
git clone https://github.com/joshuawyadao/Untapped-MacOS-Harness.git
cd Untapped-MacOS-Harness
git config --local core.hooksPath .githooks
git switch -c feat/short-description
```

The local hook blocks pushes that update or delete `main` on any remote. GitHub also enforces the protected branch rules independently of local hooks.

## Make a change

1. Start a focused branch from the latest `main`; use `feat/`, `fix/`, or `docs/` with a short description.
2. Explain the problem and include reproducible evidence. Use synthetic or redacted data for integration fixtures.
3. Update relevant documentation and add behavior tests when changing executable harness behavior.
4. Run the checks below, commit the intended files, and push your branch.
5. Open a pull request targeting `main` and complete its checklist.

```sh
python3 scripts/check_repository.py
git diff --check
git add path/to/your/file
git diff --cached --check
git commit -m "Describe the change"
git push -u origin HEAD
```

The checker examines tracked files, so rerun it after staging new files. It rejects common sensitive filenames, private-key material, large files, and broken relative Markdown links. It is a hygiene check, not a complete secret scanner. No harness build or game integration suite exists yet.

PRs require `CI Verify` from GitHub Actions, an up-to-date branch, and resolved review discussions. Squash merging is the only enabled merge method. Human approvals are optional while the project has a solo maintainer; PRs remain mandatory. Maintainers merge through GitHub after reviewing the final diff and check results.

## Reports and sensitive material

Use the issue templates for bugs and proposals. Include macOS version, processor architecture, relevant game/companion versions, reproduction steps, and expected versus actual behavior when available.

Use [private vulnerability reporting](https://github.com/joshuawyadao/Untapped-MacOS-Harness/security/advisories/new) for security issues. Follow the [security policy](SECURITY.md) before attaching logs, screenshots, or captures. Keep credentials, account details, game saves, and proprietary software out of commits and public reports.

Contributions to original project work are provided under the repository's [MIT License](LICENSE). Include attribution for permitted third-party dependencies and assets.
