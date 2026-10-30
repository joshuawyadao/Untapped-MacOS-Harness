# Verification and reward milestone

This record distinguishes static inspection, startup, game detection, reader attachment, state reading, and overlay display. Each requires separate evidence. The pinned user-supplied companion was `3.12.3-latest` with `app.asar` SHA-256 `ca3a2e6a6f728b2d635abfc70a5434d4107438b8d801a650357989e8442d798c`.

| Milestone | October 30, 2026 result | Evidence or next check |
| --- | --- | --- |
| Static inspection | Verified | Exact archive hash, guarded STS2 gates, bundled overlay/reader, and both Electron fuse wires `10110001` reproduced. |
| Source and preparation | Verified | Source signature valid outside the Codex sandbox; a copy-only patched session was prepared. Signature checks inside the Codex sandbox were misleading, so that environment is not used to judge vendor validity. |
| Offline policy | Smoke-tested | Real-home read, outside write, and remote IP socket denied; session write and loopback allowed. |
| Companion startup | **Blocked by Gatekeeper before JavaScript** | An unlocked 45-second retry still produced no bootstrap or log. A sampled 20-second reproduction was rejected by Gatekeeper according to targeted `syspolicyd` logs. Outside-sandbox `codesign` and `spctl` identify the patched ASAR as an invalid sealed resource. |
| Native game window detection | Untested | Requires a `window-detected` event from the copied companion. |
| Reader attachment | Untested | Requires `attach-attempt`, then `reader-connected` after vendor `connect()` reports success. The `status` label is `CONNECT_ACKNOWLEDGED`: native connection and runtime wrapper setup were acknowledged, but later game-context traversal remains unproved. Window detection alone is insufficient. |
| Reward state | Untested | Requires a real `reward` event with card IDs, upgrades, and normalized positions matching the visible game screen. |
| Overlay and recommendations | Untested | Need visual overlay evidence and separate advice validation; neither follows from a reward event. |

The preparation made no signing or entitlement change. No game was launched, no save was read, no terms were accepted, and no account or run was uploaded. Thirty synthetic tests passed, including Node VM execution of the original bootstrap against stubs and ten signing tests with all codesign calls mocked. Vendor code and native modules were not executed in that suite. The CI test job checks portable harness behavior and repository hygiene, not macOS game compatibility.

The earlier locked desktop prevented UI inspection but was not the startup cause. The unlocked desktop inventory showed no companion window. A process sample contained only `_dyld_start`, a 96 KiB footprint, and no loaded-image listing; a minimal Electron run-as-Node probe stalled before companion JavaScript as well. The decisive evidence is the OS log's explicit Gatekeeper rejection, supported by the invalid-resource assessments. Nested helpers/frameworks verified. No OS warning was approved or bypassed.

## Proposed next step: requires owner approval

For one fresh disposable session, re-sign **only the outer companion bundle** ad hoc while retaining Hardened Runtime and its five existing true entitlements: debugger, JIT, unsigned executable memory, DYLD environment variables, and disabled library validation. Add no entitlement, including `get-task-allow`. Do not sign the game or recursively sign nested code.

The reviewable command produced by `signing-proposal` has this form:

```sh
/usr/bin/codesign --force --sign - --options runtime --timestamp=none \
  --entitlements /private/tmp/untapped-sts2-session/companion-entitlements.plist \
  /private/tmp/untapped-sts2-session/Companion.app
```

Only after explicit owner approval, `python3 -m harness.cli sign-copy /private/tmp/untapped-sts2-session --approve-ad-hoc-signing` executes that operation, verifies both architectures' entitlements and the nested code, and writes `signing.json`. Launch accepts the specific resulting executable hash while retaining its ASAR/framework/native-reader guards and re-verifying the signed copy. The receipt records the local operation; it is not an authorization credential or vendor trust.

Ad-hoc signing replaces Untapped's Developer ID identity for that copy and provides no vendor notarization. Gatekeeper may still require a separate user decision. No signing command, warning exception, quarantine removal, or global protection change has been performed. Roll back by discarding only the disposable session. Apple's [code-signing guidance](https://developer.apple.com/library/archive/technotes/tn2206/_index.html) distinguishes signing nested code from recursive verification.

## Commands and private evidence

Use the commands in the [README](../README.md). `inspect` prints pinned-source observations. `prepare` creates `manifest.json` inside a fresh private session. `launch` is single use per session; it returns a nonzero status if `ready` is not observed. `ELECTRON_READY` means Electron reached its readiness callback; it does not prove Untapped's UI or services finished initializing. `status` reads only that session's private events and log. A manifest records static preparation, not proof of startup. Do not commit or publish session logs, events, screenshots, or a modified companion copy without reviewing personal data and third-party rights.

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
