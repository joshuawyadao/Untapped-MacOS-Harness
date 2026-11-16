# Plan

Verify the macOS-native launcher alongside the portable suite while preserving the CI Verify gate.

## Scope
- In: Scoped CI enforcement, automated validation, meaningful orchestration regressions, and canonical verification documentation for Untapped MacOS Harness.
- Out: Product feature changes, deployment, paid services or account changes, personal data, physical-device operation, and release signing/publishing.

## Action items
- [ ] Read native installer, gateway, credential-boundary tests, and Desktop-Launcher documentation.
- [x] Add an isolated native compile/ad-hoc signature verification helper without launching components or using Keychain.
- [x] Run native outcome tests on macOS and portable tests on Ubuntu behind one unconditional aggregate gate.
- [x] Add regression checks for orchestration and document exactly what native validation proves.
- [ ] Run portable tests and safe local native compilation; validate YAML and diff.
- [ ] Save and push the isolated branch; validate hosted workflow when available.

## Discovery notes
- Baseline: `a1a6849a837b3a62fde14e81df135476529a6163` (`HEAD`), isolated from the original checkout.
- Existing in-progress changes in original project folders remain untouched.
- Missing hosting/account capabilities are reported as concrete limitations; they are not permission to weaken required checks.
- The local macOS native compilation, signature verification, and outcome tests passed. The full local portable suite encountered unrelated sandbox loopback denials and an x86-only Node selected from `/usr/local/bin`; hosted Ubuntu verification remains pending.
