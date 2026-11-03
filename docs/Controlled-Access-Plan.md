# Controlled manual sign-in and public-data test

## Approved and staged state

**Revision08b is staged for owner review and a bounded manual retry.** It restores the original companion HTTP User-Agent at the gateway after a header-dependent403 rejection was reproduced. Its app tree and signing receipt are byte/mode/symlink identical to signed copy08; no new signing, ASAR change or entitlement change was performed. The preparation is at `/private/tmp/untapped-native-sts2-poc-08b/Companion.app`. Its ASAR SHA-256 remains `1c343975300061b01917f5258d9f03089c0bb7ed9e21471e9560f055eeb02720`. Original framework/native binaries, Info.plist, both original entitlement sets and Hardened Runtime are retained. The read-only source image remains detached.

The owner approved the original copy08 `signing-proposal.json` and `controlled-access-proposal.json` at `/private/tmp/untapped-native-sts2-poc-08`, including its first bounded manual sign-in probe. Revision08b's changed helper proposal is a separate review item before the owner initiates a retry; no new app signature is needed. Deep strict signature verification, both architectures' original five entitlements, native payload pins and revised gateway/adapter hash binding pass. Signed executable SHA-256 remains `5cc4476cf26ea005a0d4d69021dc9b70a6c7cf939fe9a7e348eb402aed8f3383`.

The revised `companion08b.tar` and checksum are staged at `/private/tmp/untapped-sts2-transfer-01`, together with current original helpers and `controlled_sign_in.sh`. Archive SHA-256: `8d1587fb765e9f008258b72bd2c8fea3ff44b3cf8747c4d41963165f3097939a`. All333 entries were checked for type/mode/content or symlink target; a private exact-mode extraction reproduced the unchanged signed tree and passed signature/payload verification. The archive contains only Companion.app, revised manifest.json and unchanged signing.json, with no profile, Terms, account or logs. The old companion08 archive/manifest are preserved, as are copy07 and the approved debug game. No revision08b app or live OAuth attempt has run yet.

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

Revision08b sets one fixed User-Agent inside that transport: `node-fetch/1.0 (+https://github.com/bitinn/node-fetch)`, the default in the pinned original companion library. The new gateway SHA-256 is `70d78c4798db97790fead4e22a41e061c241f2f3373f18aac6d5f46ff9c3cdd3`; the adapter remains unchanged. Caller-supplied User-Agent remains disallowed. This revision changes no destination, method, body shape, credential scope, proxy/redirect/TLS handling or app sandbox rule. The private `controlled-access-proposal.json` exposes the fixed value and previous hash for review. The old manifest is not silently rewritten: its stale hash is refused by current helpers, and the revised launcher explicitly selects companion08b.

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
3. Review the fixed-header revision above. In `sts2test`, close Steam and every game copy, then run `/bin/sh /private/tmp/untapped-sts2-transfer-01/controlled_sign_in.sh` to opt into the bounded login-only retry with companion08b. A later combined reward test uses `--observe-debug-game` with the already verified debug game paused at a reward. This flag verifies that exact game receipt/PID/path/user before attachment.
4. Review Terms manually. Use the companion's sign-in control; Terminal now prints a complete cat command containing only the new private URL-file path. Run it in another Terminal and open the resulting URL yourself in the test-account browser. Do not reuse an old URL or paste it into this chat. Finish the vendor's sign-in/consent yourself; do not approve unrelated OS prompts.
5. The companion runs at most300 seconds and closes at most45 seconds after the original auth callback reports success, whichever limit comes first. No gameplay is automated. All app descendants and the local gateway are supervised/closed.
6. Send only the sanitized Diagnostic file path. Startup without a real authenticated event is not reported as a successful sign-in; a later nonzero native exit also fails the probe. Do not infer overlay success from authentication alone.

The first approved login-only command ran in UID502 and failed. Its result and saved-error classification have been reviewed; the header correction is prepared, but a successful token exchange is not yet established. The owner initiates the revised attempt after reviewing this change. The assistant does not launch it from UID501 or automatically retry sign-in.

## First live sign-in result and read-only follow-up

The sanitized `sts2test-controlled.7a7o1dnx.json` records bootstrap/ready/manual-sign-in-ready, Core initialization, no startup blockers, companion exit0 and complete gateway cleanup. One request reached route oauth_token and received HTTP403; no local denied-route count or authenticated event followed. The vendor browser and companion displayed authentication failure. These counters distinguish an upstream HTTP rejection from this gateway's allowlist rejection, but do not identify the upstream reason. No account or public-data request is recorded; the login-only settings/cache flags do not establish game compatibility.

The original `harness.auth_diagnostic` command reads only the last2MiB of stdout.log and profile/log.log in an owned0700 controlled attempt. It refuses redirected, linked, nonregular or other-owner inputs, verifies the controlled launch metadata, and examines bounded token-grant error bodies. The shared `sts2test-auth-error.*.json` contains only fixed HTML/browser-challenge/provider markers, known OAuth error codes, original completion/failure booleans and input-limit counters. No response text, URL, header, account value or unknown error code is copied. This is a read-only saved-data check: no app launch, sign-in or network request, and no signed payload/policy change. A security-page marker is evidence of page content, not proof of the rejection's cause.

The owner ran the classifier. `sts2test-auth-error.sab2rzl0.json` reports UNCLASSIFIED_TOKEN_ERROR, a logged token failure and callback failure, no completed token exchange and no HTML/challenge/provider/known OAuth markers; both bounded input logs were read without truncation. This does not identify the body or rejection reason, and no raw text was shared.

Two subsequent credential-free GETs to the same already reviewed account endpoint changed only User-Agent: Python's default received403 text/plain (17 bytes), while the pinned original companion value received401 application/json (85 bytes) with the standard missing-credentials message. They used normal TLS, no redirects and no account/token/cookie/body/query. This proves a header-dependent rejection on that endpoint, not a successful OAuth exchange or the internal reason for the upstream rule. An inert on-wire regression reproduces403 before the correction and401 afterward. The next useful step is the reviewed owner-run retry, not another saved-log export.

## Geometry and remaining limits

The recorder now retains scaleX/scaleY alongside GlobalUi-normalized control centers and raw hitbox sizes. `compare-reward` with expected `geometry_space: rendered-hitbox` requires scales and compares width×abs(scaleX) and height×abs(scaleY). Expected card bounds must be independently transcribed from the complete game content viewport, accounting for borders/letterboxing; painted artwork may differ from its hitbox. Legacy raw comparisons are explicitly labeled RAW_ONLY_INCOMPLETE rather than treated as rendered validation.

The prior CloudSaveStore/settings property error can independently leave the vendor overlay's target resolution unavailable. This setup does not patch that compatibility issue or bypass login/feature checks. The first live OAuth attempt failed; authenticated account/features population, public-data parsing, overlay rendering/alignment, ratings/advice and broad run tracking remain unverified. Sign-in alone is not proof of a visible overlay.

## Verification so far

All134 portable tests pass, including synthetic JS auth/credential/upload/metric boundaries, original adapter URL validation, gateway default-deny/payload/header/redirect/cache/size/deadline/concurrency tests, supervisor cleanup, sanitized exports, saved-error privacy checks, scaled comparisons and the new original-client-header regression. Test traffic uses only fake/local servers; the two real credential-free diagnostic GETs above are separate evidence. The launcher instruction test verifies a complete path-only cat command and excludes the gateway secret. Copy08's exact three changed JS entries passed Node syntax checks; revision08b retains that entire signed app tree and receipt unchanged. Signed archive extraction and revised hash binding pass. The corrected owner-run sign-in result remains pending.
