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
- Launch disposable companion copies only through the guarded CLI supervisor. Native Electron can initialize before the JavaScript environment guard; opening a copy directly or through an app-launching UI API is not confined by that guard. Use non-launching observation during bounded probes.
- Review the staged diff before every commit. Ignore rules do not protect a file already tracked by Git.
- GitHub secret scanning and push protection cover supported secret patterns. The local checker adds filename and private-key checks; neither guarantees that all sensitive data will be detected.

If a credential is exposed, revoke or rotate it immediately and notify the maintainer privately. Removing it from a later commit does not remove it from existing Git history or copies.

## Explicit debug-game experiment

The default launcher still requires an unchanged prepared game. The separate `game_debug` path requires an exact full original-tree pin, a fresh private copy and explicit owner approval before signing. Its one proposed new entitlement, `com.apple.security.get-task-allow`, permits debugger task-port access to that copy while running; it does not change global macOS protection settings. The planned inspector/reader use is limited to the dedicated test account and exact copied PID/path. A signing receipt records verified bytes and settings, not owner authorization.

Signing is outer-only and must preserve Hardened Runtime, original entitlements, all nested payloads and file modes. Only the outer executable signature and its CodeResources seal may change; all other tree entries must match. Default launches reject debug metadata without explicit opt-in, and debug launches/observations require the exact separate installed path plus matching private baseline, receipt, signatures and complete post-signing tree. No game signing or new launch occurred while preparing this proposal.
