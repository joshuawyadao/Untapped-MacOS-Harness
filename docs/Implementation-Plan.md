# Plan

Repair the desktop launcher's live status stream so Steam readiness prompts arrive while its worker is running, preserving ordered final output and game/account safety checks.

## Scope
- In: Native pipe reader, interactive streaming regression, native build/validation, staged launcher update and verification docs.
- Out: Backup/source/account checks, progress or game modifications, saved credentials, unrelated refactoring.

## Action items
- [x] Reproduce the actual native reader failure using a cat child that emits one status line and remains open awaiting input: status_delivered_while_worker_waits=false.
- [x] Checkpoint this plan and preserve the existing installed session.
- [x] Test the ranked buffering hypothesis by replacing fill-oriented Foundation reads with interrupt-safe POSIX reads, retaining one ordered producer.
- [x] Add the interactive streaming case to the actual Swift regression alongside final-message/exit ordering; prove red then green.
- [x] Compile the app, run the native regression, full Python suite and repository checks; update verification and save/push this branch.
- [x] Build/sign and install the update after cancelling the waiting worker through Stop Companion; preserve the previous app and verify installed signature/runtime files and idle UI. The interactive native regression establishes live status delivery; the owner runs the next actual Steam readiness sequence.

## Open questions
- None. The isolated streaming fixture excludes backup and JSON parsing as causes; no game is launched by the fixture.
