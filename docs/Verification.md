# Verification and reward milestone

This record distinguishes static inspection, startup, game detection, reader attachment, state reading, and overlay display. Each requires separate evidence. The pinned user-supplied companion was `3.12.3-latest` with `app.asar` SHA-256 `ca3a2e6a6f728b2d635abfc70a5434d4107438b8d801a650357989e8442d798c`.

| Milestone | October 30, 2026 result | Evidence or next check |
| --- | --- | --- |
| Static inspection | Verified | Exact archive hash, guarded STS2 gates, bundled overlay/reader, and both Electron fuse wires `10110001` reproduced. |
| Source and preparation | Verified | Source signature valid outside the Codex sandbox; a copy-only patched session was prepared. Signature checks inside the Codex sandbox were misleading, so that environment is not used to judge vendor validity. |
| Offline policy | Smoke-tested | Real-home read, outside write, and remote IP socket denied; session write and loopback allowed. |
| Companion signing | **Verified after owner approval** | Only the outer disposable companion was re-signed ad hoc. Deep strict verification, both original entitlement sets, and fixed framework/native/ASAR hashes passed. |
| Companion startup | **Electron ready; Core/UI not observed** | The approved signed copy emits bootstrap/ready, then exits 0 before Core initialization. Socket-directory creation and child Seatbelt initialization fail. No companion window appeared. |
| Native game window detection | Untested | Requires a `window-detected` event from the copied companion. |
| Reader attachment | Untested | Requires `attach-attempt`, then `reader-connected` after vendor `connect()` reports success. The `status` label is `CONNECT_ACKNOWLEDGED`: native connection and runtime wrapper setup were acknowledged, but later game-context traversal remains unproved. Window detection alone is insufficient. |
| Reward state | Untested | Requires a real `reward` event with card IDs, upgrades, and normalized positions matching the visible game screen. |
| Overlay and recommendations | Untested | Need visual overlay evidence and separate advice validation; neither follows from a reward event. |

The initial preparation made no signing change; the outer signature was later changed only with explicit owner approval. No entitlement was added. No game was launched, no save was read, no terms were accepted, and no account or run was uploaded. Thirty-six synthetic tests passed, including Node VM execution of the original bootstrap against stubs, ten mocked signing tests, and six startup-diagnostic tests. Vendor code and native modules were not executed in that suite. The CI test job checks portable harness behavior and repository hygiene, not macOS game compatibility.

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

## Next experiment: requires separate approval

The signed copy's failure is now reproducible after Electron readiness. `stdout` reports a failed socket directory and child `sandbox initialization failed: Operation not permitted`; the vendor log incorrectly infers an existing instance from the failed lock. A minimal Node-mode diagnostic on the same signed executable succeeds. The runtime identifies Electron 37.10.3 and Chromium 138.0.7204.251.

Chromium's [macOS temp-path implementation](https://raw.githubusercontent.com/chromium/chromium/main/base/files/file_util_apple.mm) checks `MAC_CHROMIUM_TMPDIR` before `NSTemporaryDirectory`; the CLI now redirects that to a short session-local `t/` directory. A synthetic AF_UNIX bind was denied by the original IP-only policy. A proposed session-path-only socket allowance passed positive/negative probes: inside-session bind allowed; outside-session socket connect, remote-IP connect, real-home read, and outside write denied. IP binding behavior did not change; those finite probes do not establish every inbound-network property.

The independent child failure has a different mechanism: [Electron's exact helper entry point](https://raw.githubusercontent.com/electron/electron/v37.10.3/shell/app/electron_main_mac.cc) initializes Chromium's Seatbelt policy, and the installed `MacOSX27.0.sdk/usr/include/sandbox.h:25–27` documents that a process already in a sandbox cannot initialize another profile this way. Redirecting temp files or allowing private sockets does not resolve it.

The next proposed command is for the **same already signed disposable app**, with a fresh empty profile, `MAC_CHROMIUM_TMPDIR` inside its session, session-path-only Unix IPC, the outer offline/home/write confinement retained, and **`--no-sandbox` for Chromium child processes**. The children inherit the outer policy, but lose Chromium's separate process sandbox. This is a security tradeoff, not equivalent protection. No global protection, installed game, saved run, or remote network access is included.

The exact unexecuted command/environment/policy are prepared privately in the session's `next-launch-proposal.json` and `offline-next-proposal.sb`; no proprietary material or private profile belongs in Git. It uses the following command form, with the profile argument pointing to a new empty profile:

```sh
/usr/bin/sandbox-exec -f /private/tmp/untapped-sts2-session/offline-next-proposal.sb \
  '/private/tmp/untapped-sts2-session/Companion.app/Contents/MacOS/Untapped.gg Companion' \
  --user-data-dir=/private/tmp/untapped-sts2-session/next/profile --no-sandbox
```

The raw command must run through the bounded process-group runner with a 45-second timeout and group cleanup; it has no timeout by itself. That flag has not been passed to the app, and the default CLI still uses both layers. The previous signing approval does not authorize disabling Chromium's sandbox. Stop for explicit approval of this next experiment; terms acceptance and live gameplay still have their own boundaries.

## Commands and private evidence

Use the commands in the [README](../README.md). `inspect` prints pinned-source observations. `prepare` creates `manifest.json` inside a fresh private session. `launch` is single use per session; it returns a nonzero status if `ready` is not observed or a known startup blocker is logged. `startup_blockers` distinguishes socket-directory and child-sandbox errors. `companion_initialization` reports only observed Core/terms log milestones, which still need visual confirmation. `ELECTRON_READY` means Electron reached its readiness callback; it does not prove Untapped's UI or services finished initializing. `status` reads only that session's private events and log. A manifest records static preparation, not proof of startup. Do not commit or publish session logs, events, screenshots, or a modified companion copy without reviewing personal data and third-party rights.

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
