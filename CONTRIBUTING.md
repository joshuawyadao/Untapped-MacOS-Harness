# Contributing

This project investigates native macOS compatibility between the official Untapped.gg companion and Slay the Spire 2. Reproducible evidence and focused original-code contributions are welcome.

## Local setup and checks

Install Git, Python 3.9 or newer, and Node 18 or newer for the stubbed bootstrap test. The harness CLI uses only Python's standard library; neither vendor software nor the game is needed for CI and synthetic tests.

```sh
git clone https://github.com/joshuawyadao/Untapped-MacOS-Harness.git
cd Untapped-MacOS-Harness
git config --local core.hooksPath .githooks
git switch -c feat/short-description
python3 -m unittest discover -s tests -v
node --check harness/bootstrap.cjs
python3 scripts/check_repository.py
git diff --check
```

The local hook blocks pushes to `main`. Repository hygiene checks examine tracked files, so rerun after staging new files. They detect common sensitive paths, private-key material, large files, and broken relative Markdown links; they are not a complete secret scanner. The test suite uses synthetic archives and Node stubs. Passing tests or `CI Verify` does not prove companion startup or game integration.

The Ubuntu CI runner provisions `/private/tmp` with sticky world-writable permissions to exercise the harness's fixed macOS temporary namespace using synthetic fixtures. Ownership fixtures use the actual test user's UID, and transport fixtures use the host's `errno` constants. Production ownership, canonical-path and private-directory checks remain enforced; Linux CI does not establish native macOS compatibility.

## Make a change

1. Start a focused branch from the latest `main`; use `feat/`, `fix/`, or `docs/` with a short description.
2. Explain the problem with the exact companion/game versions and state whether evidence came from static inspection, startup, detection, attachment, state reading, or overlay display. Use synthetic or redacted fixtures.
3. Update [architecture](docs/Harness-Architecture.md) and [verification](docs/Verification.md) when behavior or evidence changes. Add focused behavior tests for executable changes.
4. Run the checks above, stage only task files, review the staged diff, commit, and push the branch.
5. Open a PR targeting `main`; wait for the required `CI Verify` and resolve review discussions.

```sh
git add path/to/your/file
git diff --cached --check
git commit -m "Describe the change"
git push -u origin HEAD
```

PRs require a current base branch and passing `CI Verify`; squash merging is enabled. Human approvals are optional during solo maintenance. See [repository governance](docs/Repository-Governance.md).

## Vendor artifacts and privacy

Keep proprietary companion/game apps and modified distributions, real saves, account identifiers, screenshots, network captures, and raw probe logs outside Git. The prepared session belongs in a private location such as `/private/tmp/untapped-sts2-session`; do not share it as a release artifact. Review the [security policy](SECURITY.md) before publishing evidence. The repository's [MIT License](LICENSE) covers original harness work only.

Do not start live gameplay until a game-profile, saves, and Steam Cloud strategy is established. A copied app alone does not isolate them. The harness leaves terms acceptance to the user. Default preparation and launch do not change signing or debugging entitlements; optional companion-only `sign-copy` requires explicit owner approval of the [specific proposal](docs/Verification.md#companion-only-signing). Do not disable system protections globally.

The owner requested an [isolated game-profile plan](docs/Isolated-Game-Plan.md). It recommends a dedicated standard test account with both apps in the same graphical session and the game's statically verified no-Steam path. The owner has approved isolated setup and the bounded first game launch. Follow the test-account runbook; manual account creation/login is still required. Steam settings and game signing remain unchanged.

For bounded UI probes, launch exclusively through the CLI supervisor. Do not use a bundle-ID app-opening API to inspect a process that may exit during the call; it can relaunch the copy outside confinement. The bootstrap guard is not a substitute for the outer sandbox. Use non-launching inventory and manual Terms review.
