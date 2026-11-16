# Plan

Repair STS2 overlay visibility in native macOS full screen using Electron's documented panel window type, preserve the verified companion chain, and install an updated signed launcher.

## Scope
- In: STS2-only Darwin overlay window construction, immutable companion update and selection, regression coverage, signed launcher rebuild/replacement, and owner-visible full-screen verification.
- Out: Game bytes or saves, Steam/Cloud settings, login/token handling, network routes, sandbox permissions, non-STS2 window behavior, and terminating active gameplay.

## Action items
- [x] Map Desktop-Launcher, Harness-Architecture, Main-Account-Migration and Verification docs; inspect patching, login/UI update selection, native launcher building and matching tests. Live diagnosis confirms combat data and rendered Attacks content; the owner sees the U tab after exiting native full screen. Electron v37.10.3 documents the panel type for full-screen apps.
- [x] Checkpoint this resolved plan before implementation on the current feature branch (`fc0242c`).
- [x] Add a failing regression for the real window-construction patch, proving STS2/Darwin panel behavior and unchanged other platform/franchise options; retain click-through, show/hide and positive account gates. The native-option test failed without panel and passes after the scoped option patch; real pinned CORE anchor application also verifies.
- [x] Implement the guarded patch for fresh preparations and a separately signed full-screen update layered above the retained login/UI companion; validate source binding, policy/helper pins, signatures, idempotence, tampering, interrupted preparation and rollback.
- [x] Route native-launcher selection through the complete update, run targeted and full tests plus repository/whitespace checks, and update Desktop-Launcher, Harness-Architecture and Verification docs with behavior and live-test limits. All 353 tests pass; native build and live verification remain below.
- [ ] Prepare/verify the immutable companion and signed launcher build, preserve previous selections/bundles, and replace the launcher only after normal owner closure and Steam Cloud synchronization.
- [ ] Verify installed runtime parity and native signatures; test native full-screen/windowed visibility with the owner, then save/push the completed branch and report remaining limits.

## Open questions
- None. The owner requests the full-screen fix and installed launcher update. Use the existing feature branch and original entitlements; normal game closure remains an operational prerequisite for replacing the installed launcher.

## Validation notes
- All 353 tests pass. Independent read-only integration review found no concrete defect. Synthetic tests cannot establish native full-screen compositing, focus, click-through or live badge alignment.
- The separate immutable companion update is signed/verified; only CORE changes within ASAR, and earlier UI/login copies and policy/helper pins are preserved. The staged launcher and signed Keychain helper verify, with all 39 runtime sources matching implementation checkpoint `aab687f`. Replacement awaits normal owner closure and Cloud synchronization; live full-screen/windowed observation follows installation.
