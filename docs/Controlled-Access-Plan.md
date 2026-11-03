# Controlled manual sign-in and public-data test

## Approved and staged state

**Revision08c is staged for owner review: it checks the gateway before opening the companion and records safe failure details.** The08b real-login exception502 remains unexplained; both fixed-data requests completed normally in sts2test. Revision08c's app tree and signing receipt are byte/mode/symlink identical to signed copy08, with no new signing, ASAR or entitlement change. Its preparation is `/private/tmp/untapped-native-sts2-poc-08c/Companion.app`. ASAR SHA-256 remains `1c343975300061b01917f5258d9f03089c0bb7ed9e21471e9560f055eeb02720`. Original native/framework binaries, Info.plist, original entitlements and Hardened Runtime are retained; the source image remains detached.

The owner approved original copy08 signing/access and subsequently initiated08b. The new08c preflight/error proposal is a separate review item before another owner-run attempt; no new app signature is needed. Deep strict signature verification, both architectures' original five entitlements, native payload pins and revised gateway/adapter hash binding pass. Signed executable SHA-256 remains `5cc4476cf26ea005a0d4d69021dc9b70a6c7cf939fe9a7e348eb402aed8f3383`.

The revised `companion08c.tar` and checksum are staged at `/private/tmp/untapped-sts2-transfer-01` with current original helpers and `controlled_sign_in.sh`. Archive SHA-256: `5453194a1674b54386524df00080eb2a4cab5b36ec12d5e0a6d3102d05e594bd`. All333 entries match source type/mode/content/link target; a private exact-mode extraction reproduced the identical signed tree and passed signature/payload/policy verification. Only Companion.app, revised manifest.json and unchanged signing.json are archived. Previous archives/metadata, copy07 and the debug game are preserved. No08c companion or real OAuth flow has been run.

## Boundary and disclosures

```mermaid
flowchart LR
  User[Owner] --> Browser[Test-account browser]
  Browser --> Site[Vendor sign-in website]
  Browser -->|PKCE callback| App[Confined companion]
  App -->|Loopback capability| Gateway[Local allowlist gateway]
  Gateway -->|Reviewed HTTPS only| API[Account and public-data APIs]
```

The companion still has remote networking denied by its existing outer policy. A local original Python gateway outside that app sandbox can make only reviewed HTTPS requests. It verifies TLS, ignores proxy environment settings, rejects redirects (304 cache responses are allowed), bounds input/output/deadlines and strips credentials on public reads. A random per-run capability protects loopback requests. Prepared metadata freezes the exact gateway/adapter hashes; changed policy/helper code is rejected before activation or staging and requires a new review. Incoming requests are bounded to eight handlers with read deadlines; shutdown stops accepting clients, closes active local sockets and drains tracked handlers before counters are exported. Failure to drain is a failed probe, not a clean result.

The transport retains the fixed original User-Agent `node-fetch/1.0 (+https://github.com/bitinn/node-fetch)`. Revision08c pins gateway SHA-256 `79c16a7e9cacba58dfaa23b96b0446ddf9496101dd7da00a8e00c675898c85e5`; the CJS adapter is unchanged. Caller-supplied User-Agent remains denied. No destination, method/body permission, credential scope, proxy/redirect/TLS rule or app sandbox rule is expanded. The new proposal discloses the two fixed-data preflight requests and fixed-field failure evidence; old manifests are preserved and their stale hashes refused by current helpers. The launcher selects companion08c explicitly. Proposals are labeled proposal_only, separate from recorded runtime evidence.

The **browser is outside the companion gateway and sandbox**. The owner opens the exact private sign-in URL manually and controls the website's normal traffic, cookies and account consent. No browser opens automatically, no URL protocol or login item is registered, and no system Keychain access is enabled.

The genuine vendor flow requests OAuth scope **`companion:full-access`**. This implementation does not pretend that consent is a narrower vendor token scope: the gateway separately restricts what this companion can send. The vendor receives the ordinary authorization-code/refresh-token exchange, account checks and any allowed public lookup. Passwords/second-factor prompts are handled by the owner in the vendor browser flow; the assistant does not request them.

### Exact companion gateway scope

| Purpose | Method and destination | Body/credential boundary |
| --- | --- | --- |
| OAuth code/refresh | POST `https://api.accounts.untapped.gg/o/token` | Exact authorization-code or refresh fields; original PKCE/state retained; no username/password grant. |
| Global account | GET `https://api.accounts.untapped.gg/api/v1/account` | Bearer account token; no body. |
| STS2 token | POST `https://api.sts2.untapped.gg/api/v1/oauth/tokens/exchange` | Only access_token/client_id, plus bearer token. |
| STS2 account/features | GET `https://api.sts2.untapped.gg/api/v1/account` or `/api/v1/features` | Bearer token, no body. |
| Public game definitions | GET `https://sts2json.untapped.gg/data/public/latest/eng/` plus one of cards.json, relics.json, potions.json, keywords.json, localization/encounters.json, localization/enchantments.json | No credentials/body/query. Initial scope is this exact branch/version/language. |
| Event commentary | GET `https://sts2.untapped.gg/api/v1/commentary/events` | No credentials/body/query. |
| Creator tier list | GET `https://api.sts2.untapped.gg/api/v1/tier-lists/{UUID}/resolve/` | Optional single game_version query; no credentials/body. The selected tier UUID and game version are disclosed by this lookup. |

All other requests fail closed. In particular, stats and prediction POSTs carry offered cards/deck/run context and are **not public reads**; they are blocked along with run history, upload-token/claim endpoints, MTGA APIs, AWS/S3 upload bootstrap/PUT, telemetry, updates and artwork CDNs. Any later expansion needs a concrete new review. Some imagery and statistical panels will therefore remain unavailable in this first phase.

## Genuine sign-in, restricted side effects

The original OAuth PKCE challenge/verifier, state check, loopback callback (localhost/127.0.0.1 ports17791–17799), token exchange and server account verification remain intact. `shell.openExternal` accepts only the reviewed vendor authorization URL shape and writes it to private `manual-sign-in-url.txt` mode0600. It does not invent an account or authentication success.

The original keytar replacement remains in-memory. Controlled mode enumerates only entries for the exact requested credential service, enabling legitimate credentials to be read during the same app lifetime. Ordinary offline mode retains its prior empty-credential behavior. No existing account, Keychain or normal profile is imported.

A narrow controlled-mode guard omits the vendor's unrelated automatic MTGA upload-token bootstrap after successful account verification. Blocking that request alone would otherwise make the vendor remove the newly added account. Anonymous token/claims remain unavailable. STS2 save/log watching, historic upload scheduling, upload entry points and metric initialization/sends are also disabled in this mode; upload functions throw if reached rather than reporting fake success. The gateway independently denies those destinations.

## Credentials, logs and exports

The profile and raw logs remain in the owned0700 private session. Keytar credential values are kept only in process memory, but **vendor logs/settings can contain sensitive account/token material**; this is not a claim that all secrets can never reach private disk. Do not share the manual OAuth URL, raw logs/settings, headers, callback parameters or gateway capability.

The old reward script's raw-log exporter is not used for authenticated runs. `controlled.py` exports only whitelisted harness status/numeric flags, safe event names/timestamps, reward IDs/upgrades/geometry and route/status counters to `sts2test-controlled.*.json`. Raw errors/account fields/URLs/bodies/headers are excluded; CLI error output is generic. Fixed boolean categories identify the existing CloudSaveStore property error or missing public cache without copying the underlying logs. Native/third-party code could still have defects; synthetic tests do not constitute a complete audit.

Every controlled attempt starts a fresh private app profile and memory credential map. Closing the attempt loses that map; the test-account browser can retain its own site cookies under the owner's control. Retained private session folders can be discarded precisely after review; never delete another profile or game save as cleanup.

## Bounded owner-run workflow

1. Completed: apply the exact copy08 outer-only ad-hoc signing proposal, preserving original five entitlements and Hardened Runtime; verify signatures/payloads. No new game signing is needed.
2. Completed: stage only app/manifest/signing receipt as companion08.tar plus checksum, and original harness sources/script. No profile, account settings, Terms, saves or raw logs were transferred.
3. Review08c's preflight/error scope below. In `sts2test`, close Steam and every game copy, then run `/bin/sh /private/tmp/untapped-sts2-transfer-01/controlled_sign_in.sh` to initiate it. Signed-copy validation happens before network access. Two fixed-data requests pass through the same capability gateway; the companion opens only after both expected401 JSON objects pass. A failure exports a diagnostic and opens no app. A later `--observe-debug-game` mode still verifies the exact debug-game receipt/PID/path/user.
4. Review Terms manually. Use the companion's sign-in control; Terminal now prints a complete cat command containing only the new private URL-file path. Run it in another Terminal and open the resulting URL yourself in the test-account browser. Do not reuse an old URL or paste it into this chat. Finish the vendor's sign-in/consent yourself; do not approve unrelated OS prompts.
5. Signed validation/preflight time counts against the existing300-second app-attempt budget; the app receives only the remaining whole seconds. It closes at most45 seconds after genuine auth, or earlier at the remaining deadline. Cleanup still drains the gateway afterward. No gameplay is automated; descendants/gateway remain supervised.
6. Send only the sanitized Diagnostic file path. Startup without a real authenticated event is not reported as a successful sign-in; a later nonzero native exit also fails the probe. Do not infer overlay success from authentication alone.

The original login and08b retry failed. The standalone fixed-data check has completed normally; the next owner action is the reviewed08c launcher. Successful token exchange remains unverified. The assistant has not started another real sign-in or companion from UID501.

## First live sign-in result and read-only follow-up

The sanitized `sts2test-controlled.7a7o1dnx.json` records bootstrap/ready/manual-sign-in-ready, Core initialization, no startup blockers, companion exit0 and complete gateway cleanup. One request reached route oauth_token and received HTTP403; no local denied-route count or authenticated event followed. The vendor browser and companion displayed authentication failure. These counters distinguish an upstream HTTP rejection from this gateway's allowlist rejection, but do not identify the upstream reason. No account or public-data request is recorded; the login-only settings/cache flags do not establish game compatibility.

The original `harness.auth_diagnostic` command reads only the last2MiB of stdout.log and profile/log.log in an owned0700 controlled attempt. It refuses redirected, linked, nonregular or other-owner inputs, verifies the controlled launch metadata, and examines bounded token-grant error bodies. The shared `sts2test-auth-error.*.json` contains only fixed HTML/browser-challenge/provider markers, known OAuth error codes, original completion/failure booleans and input-limit counters. No response text, URL, header, account value or unknown error code is copied. This is a read-only saved-data check: no app launch, sign-in or network request, and no signed payload/policy change. A security-page marker is evidence of page content, not proof of the rejection's cause.

The owner ran the classifier. `sts2test-auth-error.sab2rzl0.json` reports UNCLASSIFIED_TOKEN_ERROR, a logged token failure and callback failure, no completed token exchange and no HTML/challenge/provider/known OAuth markers; both bounded input logs were read without truncation. This does not identify the body or rejection reason, and no raw text was shared.

Two subsequent credential-free GETs to the same already reviewed account endpoint changed only User-Agent: Python's default received403 text/plain (17 bytes), while the pinned original companion value received401 application/json (85 bytes) with the standard missing-credentials message. They used normal TLS, no redirects and no account/token/cookie/body/query. This proves a header-dependent rejection on that endpoint, not a successful OAuth exchange or the internal reason for the upstream rule. An inert on-wire regression reproduces403 before the correction and401 afterward. The next useful step is the reviewed owner-run retry, not another saved-log export.

## Revision08b result and fixed-data transport check

The owner-run08b export `sts2test-controlled.w7jrcoj3.json` contains ready/Core initialization, no startup blockers, clean exit0 and gateway cleanup, no authenticated event and only route error502 once. This is the gateway's generic exception branch, not a recorded upstream HTTP status. It does not identify whether the exception was DNS, TLS, timeout, response handling or something else.

One negative-test POST from UID501 to the reviewed token route, using only fixed nonexistent client/code/verifier data, returned the normal401 JSON invalid_client. The launcher's exact Python interpreter is3.11.2 with readable default CA file and no CA environment overrides in UID501. A separate inert local HTTP/TLS response matrix found no exception for200 keepalive, connection close, chunked or401 responses. These finite checks do not reproduce UID502's exception.

The original `harness.transport_diagnostic` checker must run in sts2test with the same interpreter as the launcher. It makes at most two existing reviewed requests: a GET account without credentials, followed by a token POST containing only fixed nonexistent client/code/verifier values. It stops before the second request if the first transport raises. Both use existing HTTPS/TLS/proxy/redirect and I/O restrictions; no app, browser, account, saved OAuth request or private log is opened. Its shared `sts2test-transport.*.json` contains only fixed response/error categories, statuses/byte counts, numeric Python version, CA accessibility/override booleans and bounded numeric error codes. It excludes raw exception messages, response text/headers, CA paths, environment values and account details. This is a diagnostic request sequence, not a real sign-in attempt or authentication result.

The owner completed that check: `sts2test-transport.lawr_85r.json` records401 JSON for both requests,85/27 bytes, the same Python3.11.2 and readable default CA file without overrides. The fixed inputs did not reproduce the exception. A separate UID501 full capability-gateway comparison also returned both401 responses with no failures and clean drain. These checks do not identify the real-flow exception or prove successful token handling.

## Revision08c preflight and safe failure evidence

The preflight sends the same two fixed-data requests through the actual listening gateway, with its per-run capability. It requires both401 bodies to parse as bounded UTF-8 JSON objects, rejecting malformed/empty/scalar/nonfinite/duplicate-key bodies. At most32768 response bytes are held privately in memory; only status/kind/byte count/json_object booleans are exported. The local sequence has a15-second deadline and stops at its first unexpected result or exception. Signed metadata/signature validation and game/Steam guards precede it. A failed check or exhausted attempt budget starts no companion.

The gateway records at most32 generic failure entries: fixed route, fixed stage (local request, upstream transport, upstream response or local response), bounded elapsed milliseconds, safe error category and optional bounded errno/certificate verification code. There are no messages, URLs, tokens, headers, bodies or arbitrary exception class names. Overflow is counted. The standalone checker reuses the same classifier. Shared output labels preflight/app counters separately and marks every failure's phase. When no app opens, all final post-drain counts/failures remain preflight, including late cleanup failures. Export still requires a complete gateway drain.

The owner-run output adds preflight, preflight_gateway_counts, gateway_failures and gateway_failure_overflow. Preflight success never substitutes for the genuine authenticated event and healthy native exit. The source review corrected JSON validation and late-error attribution; tests cover both plus closed-response portability. A real08c preflight in UID501 passed both fixed requests with no failures and clean drain, using no account/app. This is a diagnostic improvement, not a claimed fix for the real login exception. Follow the [runbook](Test-Account-Runbook.md) for the next manual attempt and send only its Diagnostic file path.

## Geometry and remaining limits

The recorder now retains scaleX/scaleY alongside GlobalUi-normalized control centers and raw hitbox sizes. `compare-reward` with expected `geometry_space: rendered-hitbox` requires scales and compares width×abs(scaleX) and height×abs(scaleY). Expected card bounds must be independently transcribed from the complete game content viewport, accounting for borders/letterboxing; painted artwork may differ from its hitbox. Legacy raw comparisons are explicitly labeled RAW_ONLY_INCOMPLETE rather than treated as rendered validation.

The prior CloudSaveStore/settings property error can independently leave the vendor overlay's target resolution unavailable. This setup does not patch that compatibility issue or bypass login/feature checks. The first live OAuth attempt failed; authenticated account/features population, public-data parsing, overlay rendering/alignment, ratings/advice and broad run tracking remain unverified. Sign-in alone is not proof of a visible overlay.

## Verification so far

All154 tests pass, including15 new gateway/supervisor preflight and privacy cases. Test traffic uses only fake/local servers; the finite real diagnostic/preflight requests above are separate evidence. Signature/archive/extraction/hash/source-parity checks pass; the signed app/receipt and CJS adapter remain identical. The08c real login result is pending, with authentication and overlay compatibility still unverified.
