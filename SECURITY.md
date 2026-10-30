# Security policy

## Supported versions

There are no published harness releases yet. Security fixes apply to the current `main` branch. A supported-release policy will be added when releases exist.

## Report a vulnerability privately

Use [GitHub private vulnerability reporting](https://github.com/joshuawyadao/Untapped-MacOS-Harness/security/advisories/new). Include the affected revision, impact, reproduction steps, and a minimal redacted example. Avoid public issues and pull requests for undisclosed vulnerabilities.

This is an independently maintained project with no guaranteed response time. Findings concerning Untapped.gg or Slay the Spire 2 themselves should be reported through the relevant vendor's security channel.

## Public repository hygiene

- Never commit credentials, access tokens, signing identities, provisioning profiles, account cookies, or private keys.
- Keep real game saves, account identifiers, unredacted logs, screenshots, and network captures outside Git. Use synthetic fixtures and redact shared evidence.
- Keep proprietary game and companion binaries or assets outside this repository.
- Review the staged diff before every commit. Ignore rules do not protect a file already tracked by Git.
- GitHub secret scanning and push protection cover supported secret patterns. The local checker adds filename and private-key checks; neither guarantees that all sensitive data will be detected.

If a credential is exposed, revoke or rotate it immediately and notify the maintainer privately. Removing it from a later commit does not remove it from existing Git history or copies.
