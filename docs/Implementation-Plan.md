# Plan

Implement a main-account launcher for the owner's existing Steam progress, with verified pre-launch backups, copied-app/process guards, genuine Steam initialization, preferences-only persistence and an explicit activation proposal before live access.

## Scope
- In: Separate copied game/companion preparation; exact main-account binding; verified private backup of the configured game-data root; genuine Steam app2868840 initialization; expected Steam namespace/profile validation for the overlay; up to4-hour companion sessions with manual normal game exit; preferences-only carry; fixed-field diagnostics; synthetic tests, docs and save-branch.
- Out: Modifying the Steam-installed app, automatic Steam/Cloud setting changes or save restore, persistent authentication/Keychain migration, broader companion API routes, automatic Terms/account consent, global OS changes, live game launch or new debugger-enabled game signing before review of the concrete proposal.

## Action items
- [x] Inspect main-account readiness, source save/Steam contracts, current test-account guards, original persistence/cleanup code and applicable tests/docs. Bind the supported source build and Steam AppID; never infer Cloud freshness from directory presence.
- [x] Checkpoint this resolved plan before implementation. Delegate only file-disjoint backup and main-companion/preferences modules/tests; keep orchestration, guarded source patches, preparation artifacts, docs and Git with the parent.
- [x] Implement bounded no-follow private backup/verification with before/after stability and exact content checks, refusing linked/changed/oversized inputs and any source/destination overlap. Require Steam and games closed while taking a backup; implement no restore command.
- [x] Implement a main-account workspace/prepare/proposal/activate/start CLI and shell entry. Pin installed and copied binaries, retain test guards, require a fresh verified backup and explicit owner Steam/Cloud/account confirmations, permit only the expected same-user game PID and abort on unexpected copies. The copied game uses normal user/Steam permissions only under the reviewed main-account opt-in; no silent sandbox fallback is added to test launchers.
- [x] Add a main-mode native settings assertion for the exact private Steam ID/current profile, exporting fixed verified/mismatch events only. Run the copied game with force-steam=on/nomods and a private working-directory AppID file; require positive initialization and cloud-store branch markers, treating these as insufficient alone for account/Cloud correctness.
- [x] Implement longer confined companion supervision using the unchanged gateway/preflight and target guard. Carry only validated STS2 preferences, actual prior manual Terms acceptance and minimal public tier-list selections into fresh short-path profiles; keep credentials memory-only. Owner/game exit, target conflict, mismatch, interrupt or deadline stops the companion and never kills the game as a save strategy.
- [x] Test meaningful backup races/privacy/links/bounds, opt-in/action ordering, Steam/target guards, preference exclusion, native settings checks, lifecycle/cleanup and safe diagnostics. Run focused/full tests and syntax/repository checks; independently review boundaries.
- [x] Prepare unsigned main-account app copies and exact signing/access proposals, verify pins/patch entries/native preservation without executing vendor code, and update README/security/architecture/migration/runbook/verification. Checkpoint and push all code/docs. Ask for activation approval only after the concrete copied-app signing, backup, normal game permissions, Steam/Cloud access and session/exit proposal is complete and reviewable.

## Open questions
- None for implementation. Existing Steam progress is the confirmed target. The owner must later confirm Cloud is up to date and the intended Steam account before starting the reviewed live command. This is distinct from implementation approval; no live signing/game/Cloud action is part of preparation.

Implementation checkpoint: plan bac00d4 precedes the code. Focused backup/preferences/orchestration/native-guard tests pass; the first integrated full suite passed217 tests before the final main-proposal timing regression. Independent review findings are fixed and regression-covered: positive verification before overlay display, immediate mismatch hiding, helper-group cleanup after leader exit/interruption, source revalidation after Steam opens, descriptor-anchored profile I/O and fixed-stage failure diagnostics. Prepared unsigned copies and exact access/signing proposal exist in the dedicated main workspace; no real save contents/backup, signing or vendor launch has run. Full native/archive verification, final docs/tests and save remain before activation review.

Final preparation evidence: all218 tests and syntax/hygiene/link/whitespace checks pass. All440 copied game entries equal the installed source; all15099 companion entries compare with exactly five packed changes and329 otherwise unchanged app entries. Main companion ASAR2daf620993d64105d37d45ce2ad3fca38bdd3ba9d13d12614438bf7408af455c. Private identity values do not appear in the public proposal; game/companion/activation receipts are absent and backups/runs/preferences empty. The source image is detached. No real progress contents, backup, native launch, signing or remote request ran. Independent review has no remaining blocking finding. README/security/architecture/migration/runbook/verification now describe the exact implementation and pending activation, normal game permissions, backup/Cloud semantics and owner normal-quit policy. Save-branch final documentation checkpoint/push follows; activation approval is the remaining owner decision, not a claim of live compatibility.


## Approved copied-app activation

The owner explicitly approved the prepared copied-game get-task-allow signing, copied-companion signing and first backed-up main-account run with normal Steam/Cloud access on November3,2026. Reuse that approval without requesting it again. Perform signing/validation now; actual backup/game launch remains owner-initiated in an interactive normal-account Terminal after factual Cloud/account confirmations.

### Scope
- In: Execute the exact prepared activate command, verify both copied apps, receipts/proposal binding and original installed-game preservation, update activation status/docs and save the branch, provide the exact start command and normal exit instructions.
- Out: Automatically starting Steam/game/companion, asserting Cloud freshness or logged-in Steam identity, accepting Terms/sign-in, save restore or expanding the reviewed access scope.

### Action items
- [x] Re-read exact proposal, unsigned verification record and current receipts; no backup/run or activation receipt exists.
- [x] Checkpoint the resolved approval/activation plan before the local operation.
- [x] Activate with --approve-main-copy-signing; verify game and companion signatures/entitlements, full trees/payloads, proposal-hash receipt and unchanged installed source.
- [x] Record completed activation and unchanged progress/empty live directories in migration/security/readiness/verification docs; run appropriate syntax/hygiene/doc checks. Existing218 tests remain applicable unless source changes.
- [x] Commit/push and give the normal-account interactive start command with owner-controlled Steam/Cloud confirmations. No additional approval is needed for the reviewed scope.

### Open questions
- None for signing activation. Live Steam initialization, profile match, Cloud/save behavior and actual tier values require the owner's first run; the launcher itself prompts after its verified backup.

Activation result: plan0886ff1 precedes the approved operation. Both copied apps were signed and their full native signatures/entitlements/Hardened Runtime, payload preservation, source tree and proposal-bound receipt verified. Only allowed outer signing files changed; installed game unchanged. Backups/runs/preferences remain empty, and no real progress contents, game/companion execution, authentication or remote requests occurred. No source/tests changed, so the existing218-test result remains applicable. Operator-sequence review confirms the first-run command, factual owner Steam/Cloud confirmations,4-hour companion default and normal game quit. Current docs now distinguish completed signing activation from pending live compatibility. Final docs/hygiene/save checks follow; no further signing approval is needed.
