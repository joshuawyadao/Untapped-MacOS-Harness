# Reviewed game-version updates

The main-account launcher keeps the original activated game and review records intact. An updated Steam installation must match a separately reviewed build; changing an installed game never silently approves a new copy.

## v0.111.1 build contract

The measured macOS release is `v0.111.1`, commit `cc1f9462`, with 444 tree entries. Its managed assembly SHA-256 is `0dba5816282c6483d9305032acbe1a9be1e5e31b505421834ef7d1e786c19abf`; its complete original tree SHA-256 is `fa13254041eb414bef4bceba413fe23aff3e0a4dbee9a86da8cb5840aeb34be4`. The tree covers bytes, file modes, directories and symlink targets. Both original architectures retain the same four entitlements, ad-hoc signing and Hardened Runtime as the earlier reviewed build.

`game_builds.py` defines the immutable reviewed build. `game_launch.verified_app` and `game_debug.prepare/proposal/sign/verify` accept that explicit build while retaining the original v0.107.1 defaults for old receipts and test-account operations. Arbitrary caller-supplied versions/hashes are rejected. Signing adds only the existing debugger attachment entitlement to the new outer game copy; nested code and other payloads remain unchanged.

## Main-account upgrade

For an already activated main-account workspace, from the compatibility checkout:

```sh
python3 -m harness.game_update --install-main --approve-debug-game-signing
```

The command requires explicit approval and the normal account. It holds the desktop session lock, requires Steam/games closed, validates the existing Steam/profile binding and activation, verifies the retained game, then prepares/signs/verifies a separate copy. It rechecks the installed source, closed-process condition and retained metadata before publication.

The new fixed directory is `game-v0.111.1`; `game-v0.111.1.json` is published last. The selection receipt binds the new signed-game receipt/baseline and fingerprints of the unchanged `main-launch.json`, `main-proposal.json`, `activation.json`, original game baseline and original game signing receipt. Incomplete publication, redirected metadata, malformed claims or changed lineage stop startup without fallback to a mismatched game. Repeating a completed installation verifies the selection rather than replacing it.

The original `game` directory, proposal/activation, companion layers, saved tier preferences, login configuration and progress directories are retained. No save restore or Steam/Cloud setting change occurs. The normal launcher still makes and verifies a progress backup before opening Steam, requires the owner's current account/Cloud confirmation, and rechecks progress/source/selected game before creating its game process. An installed launcher rebuild selects the updated game icon and includes the new verifier and selector.

Keep the old game and launcher rollback artifacts together with the original records. An older launcher rejects the newer installed Steam source rather than using an incompatible combination. Restoring a prior save or downgrading Steam is a separate operation, not part of this update. This command upgrades an existing activated workspace; legacy first-time preparation defaults remain unchanged.

## Untapped compatibility evidence

Static comparison found all 65 explicit managed game-class contracts used by the pinned Untapped reader in both versions. The reader already supports the newer combat `_turnState.IsInProgress` path with its legacy fallback. Both games bundle .NET 9.0.7 with identical `libcoreclr.dylib` and `GodotSharp.dll`.

The custom Godot 4.5.1 engine revision changed from m.12 to m.14 and executable code differs. Static managed inspection cannot certify the opaque native reader's control geometry. Exact target attachment, matching Steam/profile, plausible visible choice/reward geometry, genuine tier data and owner-visible overlays require live validation. A successful copy/signature check alone does not establish reader compatibility.
