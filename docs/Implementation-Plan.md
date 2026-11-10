# Plan

Restore companion and overlay UI assets with bounded public downloads embedded in a separately signed local copy, plus readable tooltip and checkbox fallbacks.

## Scope
- In: Fixed public UI artwork and icon fonts; offline data-URI rendering; tooltip opacity and font-independent checkmarks; guarded main-account companion update selection; synthetic tests, native package verification, docs and branch save.
- Out: Changing the running game/session, Steam saves or signing, account/Stats/upload permissions, persistent authentication, vendor asset redistribution in Git, unrestricted runtime network access.

## Action items
- [x] Trace the packaged image/font/tooltip dependencies and current main launcher/signing contracts; confirm checkbox values are enabled despite invisible glyphs.
- [x] Checkpoint the plan; implement a bounded original asset preparer and synthetic tests, delegating that file-disjoint module.
- [x] Add a guarded separately signed companion update installation/selection path, retaining original preparation and activation receipts.
- [x] Fetch only reviewed public static assets, embed them in a new private companion copy, add opaque tooltip and font-independent checkmark fallbacks, and verify all source anchors and unchanged gateway/native payloads.
- [x] Initialize bundled default tier lists for all five characters once in the updated main profile, preserving imported lists and later user changes; test preference persistence.
- [x] Run focused/full tests, JS syntax and repository checks; verify offline rendering of icons/checkmarks/tooltip background without account or game data.
- [x] Sign and install the verified companion-only update for the next main launch; preserve the active session and original copy, update migration/architecture/security/verification docs, and save/push the branch.

## Open questions
- None. The requested UI repair and existing companion-only signing approval cover this bounded update. The current game remains owner-controlled; refreshed UI becomes available on the next launcher run.

Implementation result: installed a separately signed30-asset UI copy for the next main launch, retaining the original companion and active session. Native signatures, payload preservation and renderer syntax pass. Offline component rendering confirms icons/checkmark/tooltip/fallback; the one-time character migration preserves imported lists and later user choices. Final regression/repository/save results are recorded in Verification.md. Live updated UI/metadata refresh remains the next owner-run check.
