# Plan

Repair the desktop launcher's live status stream so Steam readiness prompts arrive while its worker is running, preserving ordered final output and game/account safety checks.

## Scope
- In: Native pipe reader, interactive streaming regression, native build/validation, staged launcher update and verification docs.
- Out: Backup/source/account checks, progress or game modifications, saved credentials, unrelated refactoring.

## Action items
- [x] Reproduce the actual native reader failure using a cat child that emits one status line and remains open awaiting input: status_delivered_while_worker_waits=false.
- [ ] Checkpoint this plan and preserve the existing installed session.
- [ ] Test the ranked buffering hypothesis by replacing fill-oriented Foundation reads with interrupt-safe POSIX reads, retaining one ordered producer.
- [ ] Add the interactive streaming case to the actual Swift regression alongside final-message/exit ordering; prove red then green.
- [ ] Compile the app, run the native regression, full Python suite and repository checks; update verification and save/push this branch.
- [ ] Build a signed update beside the installed app; request companion/launcher stop through normal controls before replacement, preserve a rollback copy, and verify the corrected UI can receive startup status.

## Open questions
- None. The isolated streaming fixture excludes backup and JSON parsing as causes; no game is launched by the fixture.
