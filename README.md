# Untapped MacOS Harness

An unofficial, experimental harness for investigating whether the **existing Untapped.gg companion** can work with native macOS Slay the Spire 2.

**Status: native reward reading and controlled sign-in are verified.** Haze, Ricochet and Infinite Blades matched the earlier debug-game reward, all upgrade level0 and in order. Revision08c subsequently completed genuine authentication with token/account200 responses and clean gateway cleanup. The earlier offline observation showed no overlay; authenticated game attachment, STS2/public-data loading, visible overlay and independent scaled geometry are the next checks. The installed game and normal saves remain unchanged.

## What this repository provides

The original Python 3.9+ CLI checks a user-supplied companion against one exact release, prepares a disposable copy with narrow STS2 changes, runs a bounded offline startup probe, and reports separate milestones. It never downloads or contains the game or companion. [Harness architecture](docs/Harness-Architecture.md) explains the patches and isolation; [verification](docs/Verification.md) records what was actually observed.

Pinned companion: `3.12.3-latest`, `app.asar` SHA-256 `ca3a2e6a6f728b2d635abfc70a5434d4107438b8d801a650357989e8442d798c`. A new release requires a new inspection and pins. The official [Mac companion download](https://companion.untapped.gg/mac-releases/Untapped.gg+Companion+Stable+Installer.dmg) supplied the inspected artifact. Use your own lawful copy; keep its DMG, app, and the prepared session outside Git.

## Local diagnostic workflow

From the repository root on macOS, with the official companion app mounted or otherwise available:

```sh
python3 -m harness.cli inspect '/path/to/Untapped.gg Companion.app'
python3 -m harness.cli prepare '/path/to/Untapped.gg Companion.app' /private/tmp/untapped-sts2-session
python3 -m harness.cli launch /private/tmp/untapped-sts2-session --seconds 15
python3 -m harness.cli status /private/tmp/untapped-sts2-session
```

`prepare` requires a **new** session path outside the repository and copies only the companion; it does not change the supplied app or the installed game. `launch` is single use per session and has a 1–60 second limit. It uses macOS `sandbox-exec` with local settings/logs, blocks real-home reads and writes outside the session, and permits only loopback networking. There is no unsandboxed fallback. A launch that does not reach `ready`, or reports a recognized startup blocker, returns a nonzero status. This probe does not launch the game or accept Untapped's terms.

For a fresh, unlaunched session, `python3 -m harness.cli signing-proposal /private/tmp/untapped-sts2-session` prints the exact outer-companion signing command and prepares its entitlement plist without executing signing. `sign-copy` requires explicit owner approval and the `--approve-ad-hoc-signing` flag. It replaces only the disposable companion's outer signature with a local ad-hoc signature, preserves its original entitlements and Hardened Runtime, and records the resulting executable hash. It does not add game access or guarantee Gatekeeper acceptance. See [signing results](docs/Verification.md#companion-only-signing) and the [approved single-layer experiment](docs/Verification.md#approved-single-layer-experiment).

After separate explicit approval of the Chromium child-sandbox tradeoff, the repeatable outer-only command is:

```sh
python3 -m harness.cli launch-outer /private/tmp/untapped-sts2-session --seconds 45 --approve-outer-sandbox-only
```

This requires the signed copy and rechecks its hashes/signature. Each run creates a new private `outer-attempt-*` profile and logs, retaining the outer home/write/network restrictions and allowing Unix sockets only inside that session. It prints `attempt_dir`; pass that path to `status` to inspect the run. Never open the copied app directly in Finder or through an automation API that can launch it: native Electron initialization precedes the JavaScript guard. Observe using non-launching inventory or manual interaction. Terms acceptance remains the user's decision.

November 2 attempts record manual acceptance in separate private profiles. A new attempt does not inherit acceptance. The earlier copy04 stalled on anonymous-token retries; the latest copy05 reaches `CORE_INITIALIZED_LOGGED`. The coarser `TERMS_LOGGED` status alone does not distinguish accepted Terms from a still-open Terms screen. See the [runtime record](docs/Verification.md#successful-offline-core-initialization) for separate evidence.

Current preparation also patches offline credential acquisition to return authentication unavailable before any credential read or anonymous-token request. This preserves Terms and the existing reader, creates no login/token, and keeps remote networking blocked. Copy05 was separately approved, signed, and launched in bounded protected attempts; the latest manual acceptance proceeds to logged Core initialization. Other vendor metrics requests still fail under the offline policy, so the outer restrictions remain necessary.

For an independent reward comparison, manually transcribe the visible cards and normalized positions into a private JSON file, then compare it:

```sh
python3 -m harness.cli compare-reward /private/tmp/untapped-sts2-session /private/tmp/expected-reward.json --reward-index 0
```

See [verification](docs/Verification.md) for the exact JSON shape and evidence rules. A matching reward does not establish overlay display or adaptive advice. Use the verified separate-account workflow for live tests; a copied game alone does not isolate saves or Steam Cloud.

## Project resources

- [Contributing](CONTRIBUTING.md): development checks and PR workflow
- [Harness architecture](docs/Harness-Architecture.md): copy boundary, patches, isolation, and rollback
- [Verification](docs/Verification.md): observed results and reward comparison
- [Repository governance](docs/Repository-Governance.md): CI, branch protection, and maintainer operations
- [Security policy](SECURITY.md): handling sensitive material
- [Implementation plan](docs/Implementation-Plan.md): task checklist and validation ledger

## Ownership and licensing

Created and maintained by [Joshua Yadao](https://github.com/joshuawyadao) as an independent engineering project. Original harness code is covered by the [MIT License](LICENSE). Untapped.gg and Slay the Spire 2 belong to their respective owners. Their software, binaries, assets, account data, and trademarks are not covered by this repository's license. This project is not affiliated with or endorsed by them.

## Isolated game first boot

The approved test setup uses the [test-account runbook](docs/Test-Account-Runbook.md). `python3 -m harness.game_launch` prepares and launches only an unchanged pinned game copy in a separate standard macOS account. It refuses normal-account operation, checks copy hashes/signatures, blocks remote networking and normal-home access, and bounds the first probe to 60 seconds. Its report deliberately does not claim verified isolation. The prepared game-only transfer and manual script are outside Git.

For later reader observation, `launch-outer --target-pid PID --target-game '/absolute/copied/game/executable'` validates user/path and supplies the target guard. New preparations reject STS2 attachment without this verified identity; startup-only probes still work. The changed companion requires a fresh signing proposal before use; the existing signed copy05 does not contain this guard.

The explicit `--manual-play` option permits a maximum 900-second session for the owner-approved bounded play step. Default probes still stop at 60 seconds. The [runbook](docs/Test-Account-Runbook.md#prepared-reward-test-step) describes the staged play/observation scripts and signed target-guarded copy06. The debug-copy reader observation has now produced a real reward event; scaled geometry and overlay remain incomplete.

Copy06's first native observation failed before JavaScript with Electron helper-app discovery failure. The [layout comparison runbook](docs/Test-Account-Runbook.md#helper-discovery-layout-comparison) stages the same signed bytes in a short private tmp session and runs a startup-only 45-second check with no game/Steam present. It reached Electron readiness and Terms with the companion window visible. Reward observations now use this private-tmp layout; actual debug-copy reward IDs/upgrades are now observed; full geometry and overlay remain unverified.

Copy06 initialized Core and detected the game window, then our identity guard failed to execute `/bin/ps` inside the outer sandbox. No reader connection occurred. Copy07 replaces that command with an original same-user metadata helper, compiled privately with the installed Apple command-line tools and hash-checked before use. All 75 tests pass, including a native helper test; approved copy07 signing and transfer verification are complete; the debug-copy reader observation now records a real reward; geometry and overlay remain incomplete. See the [runbook](docs/Test-Account-Runbook.md#copy07-identity-check-retry).

## Controlled attachment-access diagnostic

Copy07 passed the identity guard but native `connect` returned false before any state was read. `python3 -m harness.attachment_diagnostic --run-original-fixtures` builds and signs only original inert fixtures, comparing target `get-task-allow` inside/outside the existing outer policy. Two native runs in UID501 denied the target without the entitlement (kernel code5) and allowed the entitled target (code0) under both policies. This supports testing the entitlement boundary; it does not establish actual game-reader compatibility. The [test-account command](docs/Test-Account-Runbook.md#original-process-attachment-diagnostic) confirms the matrix in UID502 before any separately approved game-copy signing.

## Separate game-copy signing proposal

`harness.game_debug` prepares only a fresh copy matching the complete original tree pin and produces an outer-only ad-hoc signing proposal with the original four game entitlements plus `com.apple.security.get-task-allow`, retaining Hardened Runtime. Signing requires separate owner approval and `--approve-debug-game-signing`; that exact operation is now approved, executed and verified. The prepared target is `/private/tmp/untapped-sts2-debug-game-01/SlayTheSpire2.app`.

The guarded test uses a distinct `UntappedSTS2DebugGameSession` in `sts2test`, with a verified signing receipt and explicit `--debug-game` selection. Its native detection/connection/reward read is observed. It shares that account's existing test game data without importing normal-account saves. See the [verified setup and current workflow](docs/Test-Account-Runbook.md).

The earlier copy07 capture omitted scaleX/scaleY. Current08c capture retains them, but a real scale-complete capture and an independent full game-viewport screenshot remain needed. Do not certify displayed bounds by comparing raw hitboxes with painted artwork or by using reader coordinates as their own expected values. See the [native reward evidence and remaining gaps](docs/Verification.md#first-real-native-reward-state).

## Prepared controlled sign-in setup

Copy08 now includes a controlled manual OAuth/public-data path and scale-complete capture. The companion's remote-network denial stays in place; an original loopback gateway allows only reviewed account/token and public JSON/commentary/tier-list requests. Stats/gameplay-context POSTs, uploads, telemetry and artwork remain blocked. Browser sign-in is manual and outside that gateway; the vendor requests companion:full-access consent scope. Authenticated diagnostics exclude raw logs/account/token data.

The [controlled-access review](docs/Controlled-Access-Plan.md) records exact routes, disclosures, bounded workflow and limits. All154 tests pass using fake/local test servers. The owner-run08c report confirms preflight pass, genuine authentication, token/account200 responses, no gateway failures and complete post-auth cleanup. The older08b exception's cause remains unknown. Signed app/receipt, routes and CJS adapter are unchanged; preflight uses the existing300-second budget. The [authenticated reward observation](docs/Test-Account-Runbook.md#authenticated-reward-observation-next-step) is the next owner-run step. STS2/public-data loading, game settings compatibility, visible overlay and independent geometry remain unverified.
