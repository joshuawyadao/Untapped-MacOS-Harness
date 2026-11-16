# Plan

Retry only live game-process inventory timeouts within a fixed budget, preserve immediate stops for confirmed mismatches and exits, and install the verified launcher update.

## Scope
- In: Three total inventory attempts per consecutive timeout sequence, 250 ms between retries, responsive supervision during backoff, bounded retry/recovery diagnostics, regression tests, docs and signed launcher replacement.
- Out: Retrying real game/account mismatches or other errors, accepting stale identity data, changing each inventory command's two-second timeout, startup/test-account/network retry changes, credential access, automatic game restart or termination.

## Action items
- [x] Review the live inventory guard, supervisor, diagnostic classifier and tests plus Desktop-Launcher, Harness-Architecture, Controlled-Access-Plan and Verification. The latest real report identifies GAME_PROCESS_INVENTORY/TIMEOUT, followed by a requested clean companion exit, with the game left running.
- [x] Checkpoint this resolved plan before implementation.
- [x] Add a failing synthetic timeout-then-success regression at the live guard/supervisor seam; cover timeout exhaustion, reset after recovery, non-inventory timeouts and non-timeout failures.
- [x] Retry only subprocess inventory timeouts with at most three attempts and fixed 250 ms backoff; recheck account mismatch, game/companion exit, owner stop and finite session deadline while waiting, and require a fresh successful identity check before continuing.
- [x] Extend bounded safe diagnostics to count handled timeouts, retries, recoveries and exhaustion without leaving a recovered timeout as the fatal first failure; retain immediate mismatch behavior and privacy protection.
- [x] Run focused and full tests, verify unchanged companion/login/network pins, build/sign and verify exact runtime parity; update the operational and verification docs.
- [x] Replace the installed launcher only after normal app/game closure, preserve rollback, inspect idle controls, and save/push the completed branch with live-test limits.

## Open questions
- None. The user explicitly requests bounded timeout retries and immediate mismatch stops. The chosen budget is three total attempts with 250 ms between attempts; process creation/scheduling overhead can add to the nominal per-command bounds. No active game will be stopped for installation.

## Validation notes
- The actual launcher-guard/supervisor regression failed before implementation with TimeoutExpired on the first inventory attempt. Ten focused live-seam cases now pass: recovery, three-attempt exhaustion, budget reset, immediate confirmed game/account mismatch, cancellation/game/companion exit during delay, finite deadline and non-retryable failures. No real game or credentials are used.

- All 341 tests pass. Read-only integration review found no retry safety defect; the actual callback/supervisor tests demonstrate fresh verification, three-attempt exhaustion, responsive exits and immediate mismatch stops. Native build/install and real-game recovery observation remain next.

- Implementation checkpoint `3b6e564` is complete. The native signed staged build passes deep strict verification, all 37 runtime files match, and a packaged-supervisor synthetic timeout recovery probe passes. Companion/login/network pins remain unchanged. The game remains running, so replacement awaits normal owner closure and Cloud synchronization.

- After owner-confirmed game closure/Cloud synchronization, the idle launcher was closed normally and the signed update installed under the exclusive lock. Native signatures, helper pin and all 37 runtime files verified; the previous bundle is retained for rollback. The opened idle launcher preserves Remember enabled. No game or Keychain operation ran. Real-game recovery from a future inventory timeout remains observational validation.
