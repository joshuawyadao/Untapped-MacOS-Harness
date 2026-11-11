# Plan

Correct the remembered-login bridge's vendor service name and publish a verified launcher/companion update so a new sign-in can persist and the following start can restore it.

## Scope
- In: Exact sandbox-specific vendor keytar service, independent contract regression, retained-copy helper-pin migration, signed launcher update, safe live verification and documentation.
- Out: Restarting an active game, extracting current session tokens, unrelated Keychain items, network/sandbox expansion, automatic browser sign-in or Terms acceptance.

## Action items
- [x] Trace the signed Services chunk and reproduce the service mismatch twice with a synthetic proxy/broker replay; read desktop, access/architecture and verification docs plus affected tests/updater.
- [x] Checkpoint this resolved plan on `codex/remember-untapped-login` before implementation.
- [x] Add a regression using the vendor service expression and actual launcher sandbox ID; watch persistence fail before correcting both broker/proxy service checks, retaining unrelated-service memory behavior.
- [x] Publish a helper-pin revision derived from the verified UI source with a new selection receipt; retain v1 bytes/receipts, require matching policy/signature/base bindings and reject incomplete or mismatched updates.
- [x] Run targeted contract/migration tests, original synthetic repro and full regression suite; verify the real copied bootstrap/ASAR, unchanged gateway rules and native app/helper signatures.
- [x] Build and replace the launcher only after the current session is closed; retain rollback copies, check runtime parity and idle controls, and leave initial real sign-in to the owner.
- [x] Update desktop, architecture/access and verification docs with cause, prevention and live-test limits; commit and push completed work.

## Open questions
- None. The requested fix authorizes the bridge correction and launcher update. Active gameplay stays running until the owner closes it normally; a fresh manual sign-in is required because the current session never saved its credentials.

## Reproduction evidence
- `/opt/homebrew/bin/python3 -B /private/tmp/repro-sts2-remember-service.py` returned exit 2 twice: `vendor_service_reaches_persistence=false`, fake saved-account count 0. It uses only synthetic credentials and an in-memory store.
- The signed vendor Services chunk computes `Untapped Companion native-sts2-harness` from `UC_TEST_SANDBOX_ID`; both bridge components incorrectly matched `Untapped.gg Companion`. The owner's read-only real Keychain check succeeded but returned zero accounts. No live tokens were emitted or changed.

## Validation notes
- The independent vendor-service test failed before the correction with an empty fake store, then passed after correcting both components. Nine focused broker/proxy tests and the original synthetic repro now pass; restart hydration, rotation, logout and unrelated-service isolation are covered. No real Keychain mutation or current-game interruption occurred.

- All 311 tests pass, including native launcher regressions and new legacy/v2 publication cases. Corrected helper SHA-256 is `8f750f2d036ca42a300066f227b3bf2b37bf4298527fbafb8da42dd33192a99a`. Signed local migration/build and owner-run save/restore remain next.

- Native v2 migration and staged AppKit/helper build pass signature, payload, metadata and syntax checks. Real vendor contract matches both bridge constants; v1 ASAR remains byte-identical with unchanged gateway/adapter hashes. After the owner closed the game and launcher, the verified update was installed at the original Applications path with a rollback copy. Idle UI confirms Remember remains checked and Start/Forget are enabled. Real initial save and automatic restore remain owner-run validation steps.
