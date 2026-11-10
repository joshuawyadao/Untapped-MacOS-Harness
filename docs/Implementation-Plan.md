# Plan

Build a dedicated macOS Dock launcher that runs the verified game and companion through their existing checks, replaces Terminal prompts with native controls, and allows the companion to follow the game's lifetime.

## Scope
- In: Native launcher app, private line-delimited worker protocol, GUI Steam/Cloud confirmations, manual sign-in button, game-lifetime supervision, exclusive session lock, build/install workflow and regression tests.
- Out: Steam Play interception, automatic credentials/Terms, saved credentials, game/source/signing changes, relaxed identity/network checks and claims of unattended reliability.

## Action items
- [x] Review main launcher/supervisor, migration and verification docs, asset update selection and existing orchestration tests.
- [x] Checkpoint this plan before implementation.
- [x] Add explicit game-lifetime duration with required target callback; preserve finite CLI defaults and failure/cleanup behavior.
- [x] Build the native app and private worker protocol with Start, Steam-ready, Sign in and Stop companion controls; launch Steam after backup and preserve owner Cloud/account confirmation.
- [x] Validate private sign-in URLs and open them only on the owner's Sign in action; prevent simultaneous launcher workers and never stop the game on app exit.
- [x] Add tests for game-lifetime stop reasons, GUI protocol, cancellation, duplicate starts, validation failure and safe sign-in handling.
- [x] Compile/sign and install the launcher as a separate user app; inspect startup UI without launching a game automatically.
- [x] Run focused/full tests and repository checks; document real-use limits, manual login and initial live-launch validation; save/push the refinement branch.

## Open questions
- None. Owner selected a dedicated Dock app. Steam/Cloud readiness remains an explicit native confirmation because the current launcher cannot independently prove freshness.

Validation: 272 tests passed; Swift compilation, installed signature verification and idle UI inspection passed. The game was not launched during installation/inspection. Dock pinning and the first full real-game GUI session remain owner checks documented in Desktop-Launcher.md. Final save/push is reported separately.
