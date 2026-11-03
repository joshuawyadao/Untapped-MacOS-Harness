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

## Controlled authentication boundary

The opt-in controlled path retains the app's outer remote-network denial and routes Node-fetch through a capability-protected localhost allowlist gateway. The gateway itself runs outside that app sandbox and can reach only the reviewed HTTPS method/path/body shapes in [the access plan](docs/Controlled-Access-Plan.md). Public credentials are stripped, redirects and unrelated routes denied, and resource use bounded. The normal browser used for OAuth is not restricted by that gateway. The vendor consent scope remains companion:full-access; filtering transport does not narrow the token's server-side scope.

Manual OAuth must retain genuine PKCE/state/account verification. No account gate is bypassed or success fabricated. The controlled patch suppresses unrelated MTGA upload-token bootstrap, run/history uploads and telemetry, with transport denial as a separate layer. Memory-only keytar prevents normal Keychain/profile access; private vendor logs/settings may nevertheless contain secrets. Authenticated exports must use the dedicated field whitelist, never the old raw stdout/Core-log exporter. No raw URL, body, header, email, token, OAuth state or capability belongs in shared diagnostics.

The owner approved copy08 outer-only signing and the first controlled manual authentication probe. Signing, signature/payload verification and profile-free transfer staging are complete; the first owner-run probe failed at upstream token HTTP403. No real account/API requests occurred during preparation/staging, and synthetic fixtures do not prove live or native UI compatibility. Any expansion beyond the reviewed routes remains outside that approval.

The first owner-run probe received upstream token HTTP403 with no authenticated event. Follow-up saved-error inspection uses only bounded, same-owner, no-link files under a verified private controlled attempt. Its shared export is restricted to fixed markers and known OAuth error codes; raw response text, URLs, headers and arbitrary exception values remain private. The classifier makes no requests or application/profile/policy changes. Provider/challenge markers identify text content only and must not be treated as a proven cause or authorization to bypass an upstream security check.

Revision08b restores only the original companion's fixed node-fetch User-Agent inside the gateway. It follows a two-request comparison without credentials that changed only this header (default403, original-client401). Caller-controlled User-Agent remains denied, TLS/proxy/redirect handling and route/body/credential restrictions are unchanged, and no browser identity or challenge-handling mechanism is added. The signed app/receipt are unchanged; a fresh reviewable manifest/proposal pins the revised helper hash rather than rewriting old approved metadata. Starting the revised bounded launcher is an explicit owner-run retry; it is not started automatically. This transport correction does not establish successful authentication or authorize a broader network scope.
