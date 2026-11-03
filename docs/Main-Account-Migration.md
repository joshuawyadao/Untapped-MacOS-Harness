# Main-account and Steam progress migration

The owner wants to use existing progress in the normal macOS and Steam accounts eventually. Fresh test progress is a development fixture, not the intended permanent setup. Main-account execution is not enabled by this milestone.

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

## Proposed migration phases

| Phase | Work and exit condition |
| --- | --- |
| Readiness, this milestone | Confirm the pinned game and presence of local/Steam data using metadata only. Record unresolved/redirected/inaccessible/multiple namespaces without opening progress. |
| Recoverable progress plan | Define the exact local data set, confirm Steam Cloud is up to date with the owner, quit relevant writers and prepare a private verified backup before a future live write. Do not copy test progress over normal progress or automatically restore Cloud state. |
| Main-account launcher proposal | Pin separate copied game/companion apps and exact current-user PID. Specify any debugger entitlement/signing, narrowly allowed save writes, Steam initialization/Cloud participation, profile selection, session limit, normal exit and cleanup. Keep the Steam-installed game unchanged. Prepare the exact proposal before requesting activation approval. |
| Persistent companion preferences | Retain normal Tiers/creator preferences in a dedicated private harness profile. Decide authentication storage separately; current memory-only credentials do not silently become disk or Keychain credentials. Keep the reviewed public-data gateway unchanged. |
| Bounded live compatibility | Owner confirms the expected normal profile/progression before play. Stop on an unexpected Steam-installed replacement process, profile migration, Cloud conflict, changed build or OS prompt. Confirm actual tiers, rewards, shops/upgrades, resolution changes and normal save/exit behavior incrementally. |
| Longer normal use | Expand only after live compatibility and save/Cloud behavior pass. Prefer owner-controlled normal exit; do not use the diagnostic forced cutoff as a normal save strategy. Preserve version pins and rollback instructions. |

## Steam and Cloud contract

Valve documents that the client synchronizes Cloud files around a game session and may upload matching changed files afterward. The Steam API's restart helper can cause a direct executable launch to return to the installed Steam app. The pinned managed SteamInitializer calls Steamworks InitEx; no direct managed restart-helper reference or bundled/adjacent steam_appid.txt was found. This absence does not establish that an external copy initializes the intended Steam app/account or that native/Steam components cannot launch another copy. Those behaviors must be checked for the exact copied game; neither an app copy nor a local backup establishes Cloud isolation. See [Steam Cloud](https://partner.steamgames.com/doc/features/cloud) and [Steam API restart behavior](https://partner.steamgames.com/doc/api/steam_api#SteamAPI_RestartAppIfNecessary).

Static NGame startup invokes account/profile migration and cloud sync before profile initialization; the bundled contract says cloud data can overwrite local files. A Steam-enabled boot can change progress before a menu appears, so the first boot belongs after the recoverability and activation plan, not inside the read-only inventory.

The future plan must distinguish native game save writes from companion access and Steam Cloud traffic. The companion's gateway is not a firewall for the Steam client or game. Its stats/prediction/upload restrictions remain unchanged, and no claim of adaptive advice or complete Untapped feature support follows from displaying tier badges.

## Current boundary

No main-account game/companion process, additional signing, save backup/copy/write/restore, Steam/Cloud setting change, credential persistence or broader request scope is activated here. Existing test-account guards stay intact. The next executable milestone is an exact main-account launch and progress-protection proposal, informed by the readiness result and static Steam/save contracts.

## Current readiness result

The normal-account command completed successfully on November3,2026: release/assembly `MATCH`; data root `DIRECTORY`; Steam namespace `SINGLE` with one user directory and one normal profile directory, no modded profiles; local namespace present with one user directory and no profile directories observed. No scan limit or incomplete flag was reached. These counts reveal no account/profile identifiers and do not establish save validity, active-account identity or Cloud freshness. Main launch remains disabled and Cloud state unverified. No save contents, Steam config, credentials or account logs were opened; no game/companion/network/signing/save operation ran.

Eleven focused synthetic tests cover privacy/content-open traps, missing/inaccessible/redirected/wrong-owner/ambiguous inputs, vendor FIFO/link rejection, total/per-directory bounds, generic CLI errors and no network/process/mutation calls. The first review found descriptor-reopen and FIFO risks; no-follow descriptor walks and nonblocking regular-file validation now address both. A subsequent independent read-only review found no additional blocking issue. The main-account launcher, exact signing/save-write/Cloud proposal and real tier values are subsequent implementation work.
