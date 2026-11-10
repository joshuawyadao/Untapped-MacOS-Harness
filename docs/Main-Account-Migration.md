# Main-account and Steam progress migration

The owner wants existing normal macOS and Steam progress. The main-account launcher is implemented, and the owner-approved copied-app signing and activation are verified. The first live Steam/progress run is pending. Fresh test progress is a development fixture, not the permanent setup.

## Verified starting point

Copy09 produced visible badges under Collision Course, Astral Pulse and Celestial Might in the owner's photo. Sanitized `sts2test-controlled.yzm82cgr.json` matches those IDs/upgrades/order, reports `settings_reading: OBSERVED`, `overlay_window: SHOW_RECORDED`, and no settings-property error. Genuine authentication, STS2 account/features, public definitions and tier-resolution requests succeeded; cleanup completed. The photo is separate visual evidence, while show-call events remain lifecycle evidence only. Labels appear as `?-Tier`, so actual card ratings and complete geometry are not yet verified.

The current launcher deliberately requires the standard test account and exact debugger-enabled copied game. It disables Steam, limits game play to15 minutes and the companion to45 seconds after sign-in, starts fresh companion settings and retains credentials only in memory. None of that establishes compatibility with the normal Steam installation or Cloud progress.

## Read-only readiness check

From this repository in the normal macOS account:

```sh
python3 -m harness.main_account inspect
```

`game_build: MATCH` means the pinned release version/commit and managed assembly match; it is not a full app-signature/tree or runtime validation. Reaching the scan cap conservatively marks the inventory incomplete even if the directory happened to end at that cap.

This command derives the real current home from the operating-system account record. It checks the pinned installed game's public release metadata/assembly and directory metadata under the configured game-data root. It does not open save contents, Steam login/configuration/Cloud metadata, companion profiles, account logs or credentials. It does not launch apps, sign code, make requests or write an export file. Output contains only fixed statuses, booleans and bounded counts; local paths, Steam IDs, directory names, save fingerprints and timestamps are excluded.

An existing directory is not proof of a valid or current save. A single Steam namespace is not proof that it belongs to the currently logged-in Steam account. Multiple namespaces are a selection question for the later setup; the inspector never chooses one. `steam_cloud_state` remains `UNVERIFIED` and `main_launch_enabled` remains false for every result.

The pinned game's custom Godot configuration identifies `SlayTheSpire2` as its user-data directory name. The native Mac root is under the account's Library/Application Support, outside the application bundle. Copying an app therefore does not isolate its data. Static UserDataPathProvider methods2125/2128/2130 build `user://{steam|default}/{localPlayerId}/profileN/...`, or `modded/profileN/...`. Namespace IDs remain private. The game has separate Steam/default platform namespaces and profile directories; the earlier `--force-steam=off` test path must not be treated as a route to existing Steam progress.

## Implemented main-account launcher

The launcher and signed copied apps are ready under `~/Library/Application Support/UntappedSTS2Harness`. The owner approved activation and both signatures/receipts passed native verification. The Steam-installed app is unchanged; no real progress backup or live game/companion run has occurred yet.

| Command | Behavior |
| --- | --- |
| `scripts/main_account.sh proposal` | Read the exact prepared signing/access proposal. No app launch or signing. |
| `scripts/main_account.sh activate --approve-main-copy-signing` | After explicit approval, ad-hoc sign only the outer copied game and companion. The game copy gains get-task-allow; the companion retains its five original entitlements. Hardened Runtime and nested payloads remain. |
| `scripts/main_account.sh start --approve-main-account-launch --confirm-cloud-synced --confirm-steam-account` | After activation and the owner's confirmations, require Steam/games closed, make/verify a private backup, prompt the owner to open intended Steam, revalidate source/progress, then launch the copied game and confined companion. |

Commands run from the repository in the normal macOS account. The shell wrapper has no built-in approval flags. The flags express deliberate owner opt-in, not an authorization token; signing receipts record local operations rather than consent.

### First live sequence, activation already approved

1. In the normal account, let Steam finish synchronizing the normal game's progress. Quit the game normally, wait for Cloud to be up to date, then quit Steam. Other accounts must have no Steam/game instance running.
2. Run the reviewed start command above. It refuses changed sources, missing signing receipts or conflicting processes before progress is opened.
3. The launcher copies the entire fixed Godot data root into a new private backup, verifies every payload hash and checks the source stayed stable. It then prompts you to open Steam in the intended account. Wait until Steam/Cloud is ready, then press Return. If opening Steam updates the game or changes progress, the launcher refuses the stale preparation/backup; it does not restore automatically.
4. The copied game starts directly with `--force-steam=on --nomods --windowed`, genuine AppID2868840, normal HOME and a private working-directory AppID file. **The game uses normal current-user/Steam permissions, without the test-game sandbox.** It can read/write your normal progress, and the Steam client/game can synchronize Cloud. That access is part of the approved activation proposal; the companion gateway does not confine it.
5. Positive Steam initialization and enabled-account/app Cloud-store log markers are required before starting the companion. They do not identify the Steam account or prove freshness. The confined reader additionally compares the exact private expected Steam ID and current profile. Until that positive comparison, the STS2 overlay stays hidden even if native reward data exists; null or mismatched settings invalidate the gate. A mismatch immediately hides the overlay and stops the companion.
6. Sign into Untapped manually through the private URL-file instruction. The first main run requires your own Terms choice; existing test-account acceptance/settings are not imported. Choose Tiers and an appropriate creator list. These validated choices can persist; authentication remains memory-only and is repeated next session.
7. Confirm the expected normal profile/progression in the game before playing. First-run Steam compatibility, actual tiers and Cloud save/exit remain live checks, not certified by source inspection. Stop and review any unexpected profile, migration, Cloud conflict or OS prompt.
8. Quit the game normally when done. The companion ends on game exit, owner companion Quit, target conflict, context mismatch, Ctrl+C or its session limit. **No launcher path kills the game or restores progress automatically.** If the companion ends first, the launcher explicitly says the game is still running and must be quit normally.

### Duration and persistence

The main companion defaults to4 hours, configurable with `--minutes` up to8 hours. Authentication does not shorten the session to45 seconds. The game has no forced timeout. Existing test-account commands retain their original limits and guards.

Each companion run uses a new short private tmp copy to retain the known-working Electron helper layout. Only validated STS2 booleans/badge mode, actual prior manual `acceptedTOS`, and minimal UUID/enabled/color tier selections are seeded/harvested. Account lists, tokens, Chromium state, unrelated settings, logs and cached account data are excluded. Native credentials remain memory-only; normal Keychain/profile access stays denied. Fresh public tier metadata is fetched through the unchanged gateway.

Owned process-group cleanup includes helpers after the main companion exits. Successful private attempts are removed after preference harvest; failures retain private evidence and produce a fixed-stage `sts2main-controlled.*.json` diagnostic after gateway drain. Shared output contains no Steam IDs, save paths/fingerprints, account values or raw exceptions. Cleanup failures are reported as failures. Native termination is not called a verified graceful Quit.

The launcher returns success only after authentication, Steam-account verification and complete cleanup, with a normal game exit, companion exit or session limit. Target conflicts, account mismatches and unknown or missing stop reasons return a nonzero status even if authentication and cleanup succeeded.

### Backup and rollback boundary

Backups are local owned0700 directories with0600 payload/receipt files. Copying uses held no-follow descriptors and refuses links, hardlinks, special files, wrong owners, overlaps, changes during copy and bounded size/depth/count violations. Current limits are2GiB,20,000 files,40,000 entries and depth16. The source is rechecked against the verified receipt after Steam opens and before launch. Incomplete backups have no success receipt. Private receipt hashes/relative names never enter the shared summary.

Backups are retained, with no automatic pruning or restore command. A local backup is not a Cloud rollback transaction; a later restore must consider remote state and be reviewed separately. Do not copy test-account progress over the real profile.

## Steam and Cloud contract

Valve documents that the client synchronizes Cloud files around a game session and may upload matching changed files afterward. The Steam API's restart helper can cause a direct executable launch to return to the installed Steam app. The pinned managed SteamInitializer calls Steamworks InitEx; no direct managed restart-helper reference or bundled/adjacent steam_appid.txt was found. This absence does not establish that an external copy initializes the intended Steam app/account or that native/Steam components cannot launch another copy. Those behaviors must be checked for the exact copied game; neither an app copy nor a local backup establishes Cloud isolation. See [Steam Cloud](https://partner.steamgames.com/doc/features/cloud) and [Steam API restart behavior](https://partner.steamgames.com/doc/api/steam_api#SteamAPI_RestartAppIfNecessary).

Static NGame startup invokes account/profile migration and cloud sync before profile initialization; the bundled contract says cloud data can overwrite local files. A Steam-enabled boot can change progress before a menu appears, so the first boot belongs after the recoverability and activation plan, not inside the read-only inventory.

The future plan must distinguish native game save writes from companion access and Steam Cloud traffic. The companion's gateway is not a firewall for the Steam client or game. Its stats/prediction/upload restrictions remain unchanged, and no claim of adaptive advice or complete Untapped feature support follows from displaying tier badges.

## Activated artifacts and first-run boundary

The main workspace now contains the signed separate game and companion copies, the original immutable review proposal, the private Steam/profile binding, activation receipt and native activation-verification record. The owner approved this exact scope; signing approval must not be requested again. The proposal remains a dry review document; actual operations are recorded separately in the receipts. Backups/runs/preferences remain empty until the first owner-run start.

The installed original440-entry game tree still matches pin `4892eb6c03ae851fde4f075c5ca75d9db827b84b2c651bcc9b5e62cd41add85e`. Signing changed only the game copy's executable and CodeResources, preserving original four entitlements plus approved get-task-allow, both architecture runtime flags and all nested payloads/modes. Signed game executable SHA-256: `74ba017ccac7626b9f269f8d2bf31dc2d185c64442bb18d5fa9a2abe910c6b63`.

The main companion ASAR is `2daf620993d64105d37d45ce2ad3fca38bdd3ba9d13d12614438bf7408af455c`; signed executable is `d851fe580ba09359ff9998f9d3f894d25f404fa9e995807ec4e25f4b428f0ddd`. Deep strict signatures, both exact original five-entitlement sets and ad-hoc/Hardened Runtime flags pass. Relative to signed copy09, differences are confined to the guarded ASAR, outer executable and resource seal, with file/link types and modes preserved; native reader/framework/Info.plist and other resources are unchanged. Gateway/adapter policy hashes are unchanged, and the activation receipt matches the proposal hash.

No real progress contents, backup, game/companion execution, authentication or remote request occurred during signing/verification. Main-account Steam initialization, expected live profile, actual tiers and normal save/Cloud behavior remain first-run checks. Use the start command from the normal account after your Cloud/account confirmations; no second activation approval is needed.

## Current readiness result

The normal-account command completed successfully on November3,2026: release/assembly `MATCH`; data root `DIRECTORY`; Steam namespace `SINGLE` with one user directory and one normal profile directory, no modded profiles; local namespace present with one user directory and no profile directories observed. No scan limit or incomplete flag was reached. These counts reveal no account/profile identifiers and do not establish save validity, active-account identity or Cloud freshness. Main launch remains disabled and Cloud state unverified. No save contents, Steam config, credentials or account logs were opened; no game/companion/network/signing/save operation ran.

Eleven focused synthetic tests cover privacy/content-open traps, missing/inaccessible/redirected/wrong-owner/ambiguous inputs, vendor FIFO/link rejection, total/per-directory bounds, generic CLI errors and no network/process/mutation calls. The first review found descriptor-reopen and FIFO risks; no-follow descriptor walks and nonblocking regular-file validation now address both. A subsequent independent read-only review found no additional blocking issue. The launcher and approved copied-app signing are now complete. Live Steam/account/profile compatibility, actual tier values and normal save/Cloud behavior remain unverified.

## Offline UI repair and default character lists

The main-account session has now recorded authentication, exact Steam/profile verification, native reward detection and overlay-show; the owner confirmed visible tier ratings. This verifies the tested reward flow, not subsequent Steam Cloud synchronization or a complete game run.

The missing character/game icons, invisible checkbox ticks and transparent commentary panels came from blocked remote UI assets. `python3 -m harness.ui_update --install-main` builds a separate `companion-ui` from the verified original local companion, embeds a fixed set of public artwork and FontAwesome CSS/fonts, adds font-independent checkbox ticks and an opaque tooltip fallback, then reseals only that copied companion with the same entitlements. Preparation downloads send no account data. The gateway, runtime network denial and game remain unchanged. A completed `companion-ui.json` record selects the verified update for future main launches; incomplete preparations never become active. The original companion and activation proposal remain preserved.

The next updated main session also performs a one-time tier preference migration. It fills uncovered Ironclad, Silent, Regent, Necrobinder and Defect colors from the bundled default set, preferring the author already selected (Baalorlord for the owner's existing selections). Existing enabled imported lists remain selected. Minimal public UUID/color/enabled entries trigger the vendor's normal metadata refresh; ratings and commentary are fetched genuinely. A migration marker survives preference harvest, so later manual disabling is respected. Terms/authentication are not seeded by this migration.

Finish the current game normally, wait for Steam Cloud to synchronize, and quit Steam before using the existing main start command. The new UI/default lists take effect on that launch. Manual sign-in remains required. Stats/gameplay-context routes and unreviewed dynamic artwork remain outside this UI repair.

Pending tier metadata: fresh profiles now give saved list selections a temporary `Loading tier list…` name while the native metadata request runs. This prevents Untapped's immediate settings-page sort from throwing on undefined names. Genuine refresh replaces the temporary label; it is never saved as a rating or persisted display name. An unavailable list may remain loading, but it should not blank the settings page. The signed UI update remains unchanged.

### Tier-list queue repair

Some temporary loading labels persisted because the initial default-list burst exceeded the gateway's eight active handlers and excess connections were reset. The repaired adapter queues all companion requests at four concurrent reads, holds each slot through body completion, and retries only temporary failures of public tier-resolve GETs (three attempts maximum). It preserves the genuine metadata refresh and existing selections; it does not import a deck or invent ratings. Permanent upstream errors can still leave a list unavailable.

The reviewed adapter migration changes only helper hash fields in the retained base and UI manifests, preserving originals in a private update receipt and verifying signatures/payloads before and after. The original approval and game/save state remain unchanged. A running companion retains its old helper until restarted. Companion-only restart beside the verified existing game is supported by the established supervised workflow; the owner must sign in again. Otherwise use the existing main-account start command after normal game quit and Steam Cloud synchronization.
