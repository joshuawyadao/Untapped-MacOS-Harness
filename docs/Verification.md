# Verification and reward milestone

This record distinguishes static inspection, startup, game detection, reader attachment, state reading, and overlay display. Each requires separate evidence. The pinned user-supplied companion was `3.12.3-latest` with `app.asar` SHA-256 `ca3a2e6a6f728b2d635abfc70a5434d4107438b8d801a650357989e8442d798c`.

| Milestone | October 30, 2026 result | Evidence or next check |
| --- | --- | --- |
| Static inspection | Verified | Exact archive hash, guarded STS2 gates, bundled overlay/reader, and both Electron fuse wires `10110001` reproduced. |
| Source and preparation | Verified | Source signature valid outside the Codex sandbox; a copy-only patched session was prepared. Signature checks inside the Codex sandbox were misleading, so that environment is not used to judge vendor validity. |
| Offline policy | Smoke-tested | Real-home read, outside write, and remote IP socket denied; session write and loopback allowed. |
| Companion signing | **Verified after owner approval** | Only the outer disposable companion was re-signed ad hoc. Deep strict verification, both original entitlement sets, and fixed framework/native/ASAR hashes passed. |
| Companion startup | **Core/Terms logged in protected run** | After separately approved single-layer startup, the private log records Core creating/showing its main window and Showing Terms of Service. Inventory observed the app running. Visual inspection timed out, so visible screen contents remain unconfirmed. |
| Native game window detection | Untested | Requires a `window-detected` event from the copied companion. |
| Reader attachment | Untested | Requires `attach-attempt`, then `reader-connected` after vendor `connect()` reports success. The `status` label is `CONNECT_ACKNOWLEDGED`: native connection and runtime wrapper setup were acknowledged, but later game-context traversal remains unproved. Window detection alone is insufficient. |
| Reward state | Untested | Requires a real `reward` event with card IDs, upgrades, and normalized positions matching the visible game screen. |
| Overlay and recommendations | Untested | Need visual overlay evidence and separate advice validation; neither follows from a reward event. |

The initial preparation made no signing change; the outer signature was later changed only with explicit owner approval. No entitlement was added. During the protected runs no game was launched, no save was read, no terms were accepted, and no account login or run upload was authorized or observed. The separate extra-launch incident below has unknown native profile effects. Forty-three synthetic tests passed, including Node VM execution of the original bootstrap against stubs, ten mocked signing tests, six startup-diagnostic tests, and seven approved outer-launch tests. Vendor code and native modules were not executed in that suite. The CI test job checks portable harness behavior and repository hygiene, not macOS game compatibility.

Before approved signing, the locked desktop prevented UI inspection but was not the startup cause. The unlocked inventory still showed no companion window. A process sample contained only `_dyld_start`, a 96 KiB footprint, and no loaded-image listing; a minimal Electron run-as-Node probe also stalled then. The OS log explicitly identified Gatekeeper rejection and assessments identified an invalid resource seal. After approved signing, the same runtime diagnostic succeeds. Nested helpers/frameworks verified. No OS warning was approved or bypassed.

## Companion-only signing

The owner approved re-signing **only the outer companion bundle** in one fresh disposable session. Execution succeeded, retaining Hardened Runtime and its five existing true entitlements: debugger, JIT, unsigned executable memory, DYLD environment variables, and disabled library validation. Add no entitlement, including `get-task-allow`. Do not sign the game or recursively sign nested code.

The reviewable command produced by `signing-proposal` has this form:

```sh
/usr/bin/codesign --force --sign - --options runtime --timestamp=none \
  --entitlements /private/tmp/untapped-sts2-session/companion-entitlements.plist \
  /private/tmp/untapped-sts2-session/Companion.app
```

Only after explicit owner approval, `python3 -m harness.cli sign-copy /private/tmp/untapped-sts2-session --approve-ad-hoc-signing` executes that operation, verifies both architectures' entitlements and the nested code, and writes `signing.json`. Launch accepts the specific resulting executable hash while retaining its ASAR/framework/native-reader guards and re-verifying the signed copy. The receipt records the local operation; it is not an authorization credential or vendor trust.

Ad-hoc signing replaces Untapped's Developer ID identity for that copy and provides no vendor notarization. This signed copy executed and reached Electron readiness without an OS exception. No warning exception, quarantine removal, or global protection change was performed. Roll back by discarding only the disposable session. Apple's [code-signing guidance](https://developer.apple.com/library/archive/technotes/tn2206/_index.html) distinguishes signing nested code from recursive verification.

## Approved single-layer experiment

The signed copy's failure is now reproducible after Electron readiness. `stdout` reports a failed socket directory and child `sandbox initialization failed: Operation not permitted`; the vendor log incorrectly infers an existing instance from the failed lock. A minimal Node-mode diagnostic on the same signed executable succeeds. The runtime identifies Electron 37.10.3 and Chromium 138.0.7204.251.

Chromium's [macOS temp-path implementation](https://raw.githubusercontent.com/chromium/chromium/main/base/files/file_util_apple.mm) checks `MAC_CHROMIUM_TMPDIR` before `NSTemporaryDirectory`; the CLI now redirects that to a short session-local `t/` directory. A synthetic AF_UNIX bind was denied by the original IP-only policy. A proposed session-path-only socket allowance passed positive/negative probes: inside-session bind allowed; outside-session socket connect, remote-IP connect, real-home read, and outside write denied. IP binding behavior did not change; those finite probes do not establish every inbound-network property.

The independent child failure has a different mechanism: [Electron's exact helper entry point](https://raw.githubusercontent.com/electron/electron/v37.10.3/shell/app/electron_main_mac.cc) initializes Chromium's Seatbelt policy, and the installed `MacOSX27.0.sdk/usr/include/sandbox.h:25–27` documents that a process already in a sandbox cannot initialize another profile this way. Redirecting temp files or allowing private sockets does not resolve it.

The owner separately approved a 45-second command for the **same already signed disposable app**, with a fresh empty profile, `MAC_CHROMIUM_TMPDIR` inside its session, session-path-only Unix IPC, the outer offline/home/write confinement retained, and **`--no-sandbox` for Chromium child processes**. The children inherit the outer policy, but lose Chromium's separate process sandbox. This is a security tradeoff, not equivalent protection. No global protection, installed game, saved run, or remote network access is included.

The exact command/environment/policy were prepared privately in the session's `next-launch-proposal.json` and `offline-next-proposal.sb`, checked before execution, and then run under the process-group supervisor. It remained until its 45-second limit, and the runner stopped its process group. No proprietary material or private profile belongs in Git. It uses the following command form, with the profile argument pointing to a new empty profile:

```sh
/usr/bin/sandbox-exec -f /private/tmp/untapped-sts2-session/offline-next-proposal.sb \
  '/private/tmp/untapped-sts2-session/Companion.app/Contents/MacOS/Untapped.gg Companion' \
  --user-data-dir=/private/tmp/untapped-sts2-session/next/profile --no-sandbox
```

The raw command must run through the bounded process-group runner with a 45-second timeout and group cleanup; it has no timeout by itself. The flag was used only after explicit separate approval for this copy. The default `launch` CLI still uses both layers. `launch-outer --approve-outer-sandbox-only` now provides a tested, repeatable bounded implementation: each attempt uses a new private profile, re-verifies the signed copy and fixed payload hashes, retains outer restrictions, and records its own manifest, logs, launch result, and report. Terms acceptance and live gameplay still have their own boundaries.

## UI observation incident and current boundary

The protected attempt logged `[Core] Showing Terms of Service`, but the CUA app-selection call timed out after the 45-second runner ended. A subsequent exact-path process check found one new main process and two helpers for the disposable copy; helper arguments pointed at the normal companion profile. All three were stopped once detected; no exact-copy process remained. Timing supports a CUA/LaunchServices reopen, but does not prove its provenance.

This extra instance was outside the protected runner. The compiled bootstrap would reject missing harness environment before importing vendor Sentry/Core code, but native Electron/Chromium initializes earlier. Default browser cache/preferences or native-helper activity therefore cannot be ruled out. No evidence establishes account access or uploads. The normal profile was not inspected or deleted, and no claim is made that it remained untouched. No game was launched or terms accepted.

Do not use app-opening or bundle-ID selection APIs to inspect bounded probes. Use the CLI supervisor, non-launching inventory, and manual interaction. Manual visual review and any acceptance of Untapped's Terms are required before progressing beyond startup. The approved sandbox mode does not authorize accepting terms or starting gameplay.

## Commands and private evidence

Use the commands in the [README](../README.md). `inspect` prints pinned-source observations. `prepare` creates `manifest.json` inside a fresh private session. `launch` is single use per session; it returns a nonzero status if `ready` is not observed or a known startup blocker is logged. `startup_blockers` distinguishes socket-directory and child-sandbox errors. A recorded nonzero process exit also makes the CLI fail, even if an earlier ready event was emitted; a bounded timeout is recorded separately. `companion_initialization` reports only observed Core/terms log milestones, which still need visual confirmation. `ELECTRON_READY` means Electron reached its readiness callback; it does not prove Untapped's UI or services finished initializing. `status` reads only that session's private events and log. A manifest records static preparation, not proof of startup. Do not commit or publish session logs, events, screenshots, or a modified companion copy without reviewing personal data and third-party rights.

Before a real reward experiment, establish a game-profile, save, and Steam Cloud strategy. Do not copy or symlink actual saves by default. No signing, debugger entitlement, or system protection change should follow from this record without a concrete failure and a specific reviewed proposal.

## Reward comparison contract

A later real screen can be transcribed into a private JSON file, with visible cards from left to right and normalized coordinates (`0`–`1` relative to the game screen):

```json
{
  "cards": [
    {"id": "EXAMPLE_CARD_A", "upgradeLevel": 0, "cx": 0.25, "cy": 0.5, "width": 0.12, "height": 0.2},
    {"id": "EXAMPLE_CARD_B", "upgradeLevel": 1, "cx": 0.75, "cy": 0.5, "width": 0.12, "height": 0.2}
  ]
}
```

These IDs are synthetic and do not assert actual game identifiers. Run `python3 -m harness.cli compare-reward /private/tmp/untapped-sts2-session /private/tmp/expected-reward.json --reward-index 0`, choosing the zero-based reward event to inspect. The tool sorts cards by `cx`, then `cy`, requires exact count/ID/upgrade level, and allows at most `0.03` absolute difference in each normalized center/size coordinate. It also requires preceding bootstrap, ready, window, attach-attempt, and reader-connected events. A comparison can validate the one-screen reader milestone; overlay positioning, tier lists, statistics, and adaptive recommendations need their own checks.
