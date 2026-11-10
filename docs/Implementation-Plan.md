# Plan

Make all default tier lists load reliably by bounding the companion's startup request queue and retrying transient public tier-list failures without expanding network access.

## Scope
- In: Shared bounded client queue, finite retries for reviewed public tier GETs, regression coverage, explicitly recorded adapter hash migration for the installed main-account copies, and companion-only rollout.
- Out: New routes, account/token retries, fabricated tier metadata, signing changes, game restarts, save or Steam Cloud changes.

## Action items
- [x] Trace the six reset downloads to the gateway's eight-handler cap and reproduce the ninth-request failure with a fake upstream.
- [ ] Checkpoint this plan before implementation.
- [ ] Add a shared bounded FIFO queue below the eight-handler cap; consume bounded response bodies before releasing slots; retry only transient public tier GET failures with finite backoff.
- [ ] Cover startup bursts, body completion, overflow, retries/exhaustion, permanent errors and non-idempotent requests using synthetic Node fixtures.
- [ ] Preserve pinned-policy checks and original approvals; record and verify the exact old/new adapter hashes when updating the two installed manifests, leaving signed payloads and gateway unchanged.
- [ ] Run focused and full tests, syntax/repository checks, update Controlled-Access-Plan, Main-Account-Migration and Verification, then commit and push.
- [ ] Reopen only the supervised companion when the verified game is still present, or provide the existing launcher command; require owner sign-in and report live verification separately.

## Open questions
- None. Queueing and retries remain within the already approved public tier-list access.
