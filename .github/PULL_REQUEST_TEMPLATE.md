## Problem and change

Describe the problem and resulting behavior. Link the related issue, if any.

## Validation

List checks run and results. For compatibility changes, include macOS, processor architecture, game/companion versions, and reproducible steps. Explain any checks that could not run.

## Checklist

- [ ] Run `python3 scripts/check_repository.py` after staging new files and run `git diff --cached --check`.
- [ ] Add or update behavior tests when executable harness behavior changes.
- [ ] Update documentation and describe material limitations.
- [ ] Review the diff for credentials, personal data, and proprietary assets.
- [ ] Resolve review discussions and confirm `CI Verify` passes before merging.
