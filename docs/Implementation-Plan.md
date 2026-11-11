# Plan

Add opt-in remembered Untapped login using a harness-specific macOS Keychain item and a private session credential bridge, preserving the confined companion and existing Steam/profile/network checks.

## Scope
- In: Remember-login checkbox, idle Forget control, fixed-service Keychain helper, bounded private broker, global OAuth token restore/rotation/deletion, separately signed companion adaptation, regression tests and launcher installation.
- Out: Reading existing Untapped/unrelated Keychain items, passwords, plaintext token files, tokens in process arguments/UI/logs, persistent browser profiles, Steam credentials, network expansion and automatic Terms acceptance.

## Action items
- [x] Trace the companion keytar/global OAuth contract, current memory-only bootstrap and controlled refresh route; inspect desktop, signing/update and credential tests/docs.
- [x] Checkpoint this plan before implementation.
- [x] Implement a fixed-service Security.framework helper and bounded host wrapper; default off until owner selects Remember login.
- [x] Add a session-capability Unix-socket broker and memory-first keytar proxy; persist only global access/refresh tokens, handle invalid/revoked credentials and logout, and fall back to manual sign-in on Keychain failure.
- [x] Adapt only the copied companion bootstrap with pinned helper validation, retaining its signature entitlements, original base/UI bindings and unchanged gateway/sandbox rules.
- [x] Add native Remember/Forget controls, restore/persist integration and helper packaging/signing to the standalone launcher; prevent forgetting during active sessions.
- [x] Test round-trip restart, refresh rotation, opt-out, invalid tokens, logout/forget, unsafe inputs and Keychain denial without real credentials; run native/full tests and inspect the staged app.
- [ ] Prepare/install verified updates when the current session is closed, retain rollback copies, and leave actual Keychain consent/initial sign-in to the owner.
- [ ] Update desktop, architecture, access and verification docs; save/push the branch with explicit live-validation limits.

## Open questions
- None. The requested feature authorizes an opt-in harness-specific Keychain item; real tokens are saved only after the owner enables it and signs in.

## Validation notes
- 303 tests pass using synthetic credentials and fake Keychain operations, including native live-status/lifecycle checks. Signature verification and Keychain I/O share one 20-second deadline; broker shutdown drains active writes and rejects queued rotations.
- Native build/install and idle UI inspection remain next. Real Keychain consent, first save and later automatic restore remain owner-run checks.
