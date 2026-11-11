# Plan

Address PR #3's Brooks review by preserving native terminal failures after owner stop and testing native outcome handling and installer publication before the final review/CI pass.

## Scope
- In: Native finalization state, a testable outcome seam, installer completeness/failure tests, build integration and verification docs.
- Out: Game launches, live app replacement, runtime policy changes, unrelated refactoring and resolving GitHub review threads without owner instruction.

## Action items
- [x] Review both Brooks findings and current native/installer behavior; confirm CI Verify is the active ruleset requirement.
- [x] Checkpoint this plan before implementation.
- [x] Preserve worker terminal errors and abnormal exits when owner stop was requested; test the actual native outcome seam.
- [x] Add synthetic installer checks for source snapshot completeness, compile/sign failure and existing destination preservation.
- [x] Run native seam tests, launcher compilation, focused/full Python tests and repository checks.
- [x] Save the first validated native/installer review fix as df04836 and request current-head review.
- [ ] Drain worker stdout through EOF before processing exit; test delayed status delivery using the actual native reader.
- [ ] Update verification evidence and PR change ledger, commit/push the fix, request current-head Codex review and recheck CI/mergeability.

## Open questions
- None. The PR request authorizes narrow review fixes. Installed app replacement and live gameplay are not needed for this validation.
