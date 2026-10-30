# Untapped MacOS Harness

An unofficial compatibility harness aiming to make **Untapped.gg work with the macOS version of Slay the Spire 2**.

**Status: initial development.** This repository currently contains the collaboration, security, and verification foundation. The harness has not been implemented, and working macOS compatibility has not yet been demonstrated.

## Project direction

The goal is to close the macOS compatibility gap described by the project owner and document a reproducible way to use Untapped.gg alongside Slay the Spire 2 on a Mac.

The next milestones are to:

1. Investigate how the existing companion integration detects and communicates with the game.
2. Implement the smallest viable macOS compatibility path and document its architecture.
3. Verify the integration on documented macOS, game, and companion versions.
4. Publish setup instructions, test results, and a short demonstration.

Implementation language, supported macOS versions, and installation steps will be documented after the compatibility investigation. There is no installable harness release yet.

## Explore the repository

| Resource | Purpose |
| --- | --- |
| [Contributing](CONTRIBUTING.md) | Local setup, checks, and pull request workflow |
| [Repository governance](docs/Repository-Governance.md) | Branch protection, CI, security, and maintainer operations |
| [Security policy](SECURITY.md) | Private vulnerability reporting and handling sensitive data |
| [Implementation plan](docs/Implementation-Plan.md) | Repository setup scope and validation record |
| [MIT license](LICENSE) | Reuse terms for original project work |

## Development

```sh
git clone https://github.com/joshuawyadao/Untapped-MacOS-Harness.git
cd Untapped-MacOS-Harness
git config --local core.hooksPath .githooks
git switch -c feat/describe-your-change
python3 scripts/check_repository.py
git diff --check
```

Git and Python 3.9 or newer are sufficient for the current repository checks. Application build and integration tests will be added with the harness implementation. The required `CI Verify` check currently validates repository hygiene and local documentation links; it does not verify game compatibility.

All changes enter `main` through a pull request with passing CI. See [Contributing](CONTRIBUTING.md) for the complete workflow.

## Ownership and licensing

Created and maintained by [Joshua Yadao](https://github.com/joshuawyadao) as an independent engineering project.

Original project work is licensed under the [MIT License](LICENSE). Untapped.gg and Slay the Spire 2 belong to their respective owners. This project is not affiliated with or endorsed by them, and its license does not cover their software, game assets, or trademarks.
