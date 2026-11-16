# Plan

Add bounded supervision diagnostics that identify the failing check and safe error category, preserve failure-versus-cleanup chronology, and install the verified launcher update for the next real-game test.

## Scope
- In: Named supervision/game-identity checks, fixed error classifications, first-failure retention, before/after cleanup exit evidence, safe launcher status, synthetic failure/privacy regressions, docs and signed launcher installation.
- Out: Changing guard/retry/timeout behavior, claiming a crash fix, raw exception messages/tracebacks/argv/paths/account data, credential reads/writes, companion/network/sandbox changes, restarting or terminating the game.

## Action items
- [x] Inspect supervisor, game identity callback, cleanup, desktop worker/report contract and relevant tests; review desktop, architecture, access and verification docs. The prior report records only SUPERVISE and a pre-cleanup null exit code, which cannot identify the failed operation or establish crash causation.
- [x] Checkpoint this resolved plan on the existing feature branch before implementation.
- [x] Add a finite diagnostic vocabulary and bounded classifier that preserves only check/category/numeric error evidence; test nested failures, sensitive exception data, unknown types and exception causes.
- [x] Instrument event reads, game inventory/group/owner checks, companion polling/waiting and supervisor clocks without changing outcomes; retain the first failure and separate cleanup failures/exit observations.
- [x] Surface validated check/category text in desktop error status; add supervisor, identity-callback and worker regressions for each boundary and for secondary cleanup failures.
- [x] Run targeted and full tests, privacy/whitespace/repository checks, then build/sign the source-matched launcher; verify unchanged companion/helper/network pins.
- [x] Install only with the game and launcher closed, preserve rollback, and inspect idle controls without starting a game or touching Keychain.
- [x] Update Desktop-Launcher, Harness-Architecture, Controlled-Access-Plan and Verification with schema, incident limits and next-crash instructions; commit and push the branch.

## Open questions
- None. This instruments future failures; it cannot reconstruct the exception discarded by the previous build. The owner will close any active game and launcher normally before replacement.

## Validation notes
- A new supervisor regression failed before implementation because pre-cleanup/first-check evidence was absent. Focused tests now preserve the original timeout check across a later preference error and a negative exit observed after cleanup. Ordinary wait polling timeouts remain successful checks. No real game, Keychain or network operations are used in these fixtures.

- All 328 tests pass, including new named-check, nested cause/privacy, native-exit, cleanup chronology and desktop-message cases. The first broad run found the old temporary Node shim missing; a fresh test-only Node v22.21.1 shim restored the full suite without dependency or runtime-policy changes. Signed companion ASAR, remembered-login proxy and gateway/adapter pins remain unchanged.

- The separately staged diagnostic launcher compiles and passes deep strict signature verification with 37 runtime sources. Replacement awaits the owner's normal closure of the game, companion and launcher; no process or credential is changed by preparation.

- Implementation checkpoint `95108f9` is complete. The staged app's packaged diagnostic timeout probe and byte-for-byte runtime comparison both pass. The game, companion, launcher and desktop session remain active; the owner has been asked to close them normally before the lock-checked swap. Installation and next real-failure observation remain pending.

- After owner closure, the swap initially refused a leftover copied Untapped process and an idle launcher. The exact same-user copied process exited after normal SIGTERM when its UI could not respond; the idle launcher was closed through its window. The lock-checked swap then verified signatures and all 37 runtime files, retained the prior app, and installed successfully without starting/stopping a game or accessing Keychain. The reopened idle launcher preserves Remember enabled.
