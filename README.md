# Untapped MacOS Harness

An unofficial, experimental harness for investigating whether the **existing Untapped.gg companion** can work with native macOS Slay the Spire 2.

**Status: diagnostic proof of concept; Electron startup verified, companion UI blocked.** Owner-approved ad-hoc signing of one disposable copy succeeded. It reaches Electron readiness, then exits on socket setup and child sandbox initialization failures. Game attachment, reward reading, and overlay display remain **unverified**.

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

For a fresh, unlaunched session, `python3 -m harness.cli signing-proposal /private/tmp/untapped-sts2-session` prints the exact outer-companion signing command and prepares its entitlement plist without executing signing. `sign-copy` requires explicit owner approval and the `--approve-ad-hoc-signing` flag. It replaces only the disposable companion's outer signature with a local ad-hoc signature, preserves its original entitlements and Hardened Runtime, and records the resulting executable hash. It does not add game access or guarantee Gatekeeper acceptance. See [signing results](docs/Verification.md#companion-only-signing) and the [next proposed experiment](docs/Verification.md#next-experiment-requires-separate-approval).

If a real reward event is later captured, manually transcribe the visible cards and normalized positions into a private JSON file, then compare it:

```sh
python3 -m harness.cli compare-reward /private/tmp/untapped-sts2-session /private/tmp/expected-reward.json --reward-index 0
```

See [verification](docs/Verification.md) for the exact JSON shape and evidence rules. A matching reward does not establish overlay display or adaptive advice. Live gameplay awaits an explicit game-profile, saves, and Steam Cloud strategy; do not assume a copied game isolates them.

## Project resources

- [Contributing](CONTRIBUTING.md): development checks and PR workflow
- [Harness architecture](docs/Harness-Architecture.md): copy boundary, patches, isolation, and rollback
- [Verification](docs/Verification.md): observed results and reward comparison
- [Repository governance](docs/Repository-Governance.md): CI, branch protection, and maintainer operations
- [Security policy](SECURITY.md): handling sensitive material
- [Implementation plan](docs/Implementation-Plan.md): task checklist and validation ledger

## Ownership and licensing

Created and maintained by [Joshua Yadao](https://github.com/joshuawyadao) as an independent engineering project. Original harness code is covered by the [MIT License](LICENSE). Untapped.gg and Slay the Spire 2 belong to their respective owners. Their software, binaries, assets, account data, and trademarks are not covered by this repository's license. This project is not affiliated with or endorsed by them.
