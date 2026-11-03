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

The08b retry produced a generic gateway exception502. The separate standard-account transport diagnostic makes at most two existing reviewed HTTPS requests with only fixed nonexistent client/code/verifier values and stops at the first transport exception. It accepts no URL, account data, saved OAuth material or raw log input. Output uses fixed error/response categories, bounded numeric codes and CA/runtime booleans only; exception messages, response text/headers, CA paths and environment values are excluded. It executes no vendor app, changes no system trust/TLS verification and does not alter the frozen08b gateway/adapter metadata. Its result is connectivity evidence, not account authentication.

Revision08c first validates the signed copy, then gates startup on the same two fixed-data requests through the capability gateway, requiring bounded strict UTF-8 JSON objects with401 responses. No app starts on failure or exhausted time; preflight consumes the existing300-second budget. It records at most32 generic failures with only fixed route/stage/category, bounded timing and numeric errno/verification codes, followed by an overflow count. Sanitizers reject arbitrary future fields/values; raw exception messages, URLs, headers, bodies and account/token data remain private. Counters separate preflight from companion traffic, and late no-app failures remain preflight after drain. Authentication still requires the genuine event and healthy native exit. The fresh08c manifest pins the reviewed new gateway hash; signed app/receipt, CJS adapter, allowed routes, TLS/proxy/redirect behavior and sandbox remain unchanged. Proposals are review documents rather than runtime-status assertions.

The later authenticated08c game observation produced reader-connected and reward events plus successful STS2 exchange/public definitions/tier-resolution responses. The owner reported no visible overlay. This is evidence of controlled game state access, not permission to broaden routes or export account/settings details. The fresh copy09 preparation changes only the pinned ASAR's STS2 save-store handling and Darwin STS2 settings entry, plus fixed lifecycle event names. Its store helper accepts only the exact local or cloud save-store classes and preserves errors on unsupported types; no settings, paths, scores or account state are fabricated. The existing login/feature checks, user-selected badge mode, public-data route allowlist and blocked stats/prediction/upload/telemetry paths remain intact. `settings-read`, `overlay-ready` and `overlay-show` export only event name/time; they do not certify a visible overlay. The companion's established outer-only local signing retains its original five entitlements and Hardened Runtime, with no nested, native, game or OS-security change. No copy09 live result is claimed until a bounded owner-run test.


## Main-account migration readiness

The owner selected eventual use of normal macOS/Steam progress. `harness.main_account inspect` is a read-only prerequisite, not a launcher or authorization receipt. It derives the actual home from pwd, inspects only fixed reviewed vendor/data locations and exports fixed statuses/booleans/bounded counts. Vendor release/assembly reads are separate from save metadata; save/Steam-config/Cloud/companion/auth file contents are excluded. Paths, names, Steam IDs, save hashes and timestamps never enter output. Redirected, inaccessible, ambiguous or truncated inventories remain unresolved; the inspector never selects a Steam identity, reports Cloud synchronization or enables a launch.

The [migration plan](docs/Main-Account-Migration.md) retains the installed Steam app and all existing test-account guards. Changing the username alone is not a migration. Future activation needs exact copied-app/process identity, debugger/signing scope, normal-save and Steam/Cloud behavior, recoverability, credentials and session/exit policy. A copied app can still share normal saves, and the companion gateway does not constrain Steam's own Cloud traffic. No backup/restore, save write, Cloud setting change, persistent credentials or main-account execution is performed by the readiness milestone.


## Implemented main-account launcher, pending activation

The separate main launcher preserves all test-account guards. Prepare creates only copied vendor apps, private identity/proposal files and empty runtime directories. Activate requires explicit copied-app signing approval: get-task-allow is added only to the separate game copy, while companion signing retains the original five entitlements; Hardened Runtime and nested code are preserved. The installed Steam app remains pinned and unchanged. No activation or live launch occurred during implementation.

Start requires per-session normal-progress/Steam/Cloud confirmations and a verified backup while Steam/games are closed. It prompts for owner-controlled Steam startup, then revalidates source binaries, copied signatures and source progress before launching. The copied game runs with normal user/Steam permissions, not the isolated game's sandbox; existing progress and Cloud can change before menu display. This scope is explicit in the pending proposal. The backup is local, bounded, stable, no-follow and hash-verified, with private receipts and no restore command. Source changes, links, owner errors and incomplete copies fail before game launch. Backup existence is not a Cloud rollback guarantee.

The companion retains the reviewed outer policy/allowlist and fresh short-path profiles. A positive exact native Steam ID/profile match gates STS2 display; absent/null/mismatched settings cannot use vendor display fallbacks. Unknown context never produces fabricated success. Only validated overlay preferences, actual prior main-run Terms acceptance and minimal public tier selections persist; accounts/tokens/Chromium profiles and Keychain credentials do not. Profile I/O is descriptor-anchored against ancestor replacement. The normal home comes from pwd, not inherited HOME.

The companion defaults to4 hours (8-hour cap), with no auth-shortened cutoff. All owned companion helpers are cleaned even after leader exit; interruption/cleanup errors remain explicit failures. Fixed-stage diagnostics follow gateway drain, with failed private attempts retained locally and no account/log/save data shared. Owner/game exit or timeout never kills the game; the owner must quit it normally. Stats/predictions/uploads and unreviewed companion routes remain blocked.
