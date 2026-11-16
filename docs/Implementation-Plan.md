# Plan

Verify the macOS-native launcher alongside the portable suite while preserving the CI Verify gate.

## Scope
- In: Scoped CI enforcement, automated validation, meaningful orchestration regressions, and canonical verification documentation for Untapped MacOS Harness.
- Out: Product feature changes, deployment, paid services or account changes, personal data, physical-device operation, and release signing/publishing.

## Action items
- [x] Read native installer, gateway, credential-boundary tests, and Desktop-Launcher documentation.
- [x] Add an isolated native compile/ad-hoc signature verification helper without launching components or using Keychain.
- [x] Run native outcome tests on macOS and portable tests on Ubuntu behind one unconditional aggregate gate.
- [x] Add regression checks for orchestration and document exactly what native validation proves.
- [x] Run portable tests and safe local native compilation; validate YAML and diff.
- [x] Save and push the isolated branch; validate hosted workflow when available.

## Discovery notes
- Baseline: `a1a6849a837b3a62fde14e81df135476529a6163` (`HEAD`), isolated from the original checkout.
- Existing in-progress changes in original project folders remain untouched.
- Missing hosting/account capabilities are reported as concrete limitations; they are not permission to weaken required checks.
- Local native compilation, signature verification and outcome tests passed. After selecting the installed ARM Node and allowing temporary loopback tests outside the sandbox, all 313 portable tests passed. Hosted portable, macOS native and aggregate CI Verify jobs passed: https://github.com/joshuawyadao/Untapped-MacOS-Harness/actions/runs/43938667947 . No launcher or real Keychain operation was executed.
