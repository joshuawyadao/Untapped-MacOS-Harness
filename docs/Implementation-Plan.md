# Plan

Restore companion and overlay UI assets with bounded public downloads embedded in a separately signed local copy, plus readable tooltip and checkbox fallbacks.

## Scope
- In: Fixed public UI artwork and icon fonts; offline data-URI rendering; tooltip opacity and font-independent checkmarks; guarded main-account companion update selection; synthetic tests, native package verification, docs and branch save.
- Out: Changing the running game/session, Steam saves or signing, account/Stats/upload permissions, persistent authentication, vendor asset redistribution in Git, unrestricted runtime network access.

## Action items
- [x] Trace the packaged image/font/tooltip dependencies and current main launcher/signing contracts; confirm checkbox values are enabled despite invisible glyphs.
- [ ] Checkpoint the plan; implement a bounded original asset preparer and synthetic tests, delegating that file-disjoint module.
- [ ] Add a guarded separately signed companion update installation/selection path, retaining original preparation and activation receipts.
- [ ] Fetch only reviewed public static assets, embed them in a new private companion copy, add opaque tooltip and font-independent checkmark fallbacks, and verify all source anchors and unchanged gateway/native payloads.
- [ ] Run focused/full tests, JS syntax and repository checks; verify offline rendering of icons/checkmarks/tooltip background without account or game data.
- [ ] Sign and install the verified companion-only update for the next main launch; preserve the active session and original copy, update migration/architecture/security/verification docs, and save/push the branch.

## Open questions
- None. The requested UI repair and existing companion-only signing approval cover this bounded update. The current game remains owner-controlled; refreshed UI becomes available on the next launcher run.
