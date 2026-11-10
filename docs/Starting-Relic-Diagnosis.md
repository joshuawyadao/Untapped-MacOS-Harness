# Starting-relic badge investigation

Status: visible named-tier badges confirmed by the owner on November 10, 2026. Investigation on `codex/sts2-starting-relic-badges` remained isolated from the current PR checkout. No rendering repair was needed for this observation, and none was installed. This does not establish why the owner did not see badges in earlier attempts.

## Confirmed evidence

The owner reports missing badges on the Neow starting-choice screen. Their earlier sighting at the right edge was the Untapped sidebar, not three relic ratings.

A temporary signed diagnostic copy, retaining the existing companion entitlements and controlled network boundary, confirms:

- Native layout identifies three choices: `SCROLL_BOXES`, `ARCANE_SCROLL`, and `PRECARIOUS_SHEARS`.
- The enabled genuine colorless/Regent lists cover those IDs. Their current rating is the named tier `Inconsistent`, not a letter-tier label.
- Renderer choices, tier mode and tier visibility are enabled; all three items have tier data. Room, submenu and obscuring-screen gates permit display.
- Normalized badge anchor positions resolve to x=50% and y=69.44%, 78.33%, 87.22% before the existing 3px offset.
- The diagnostic overlay window reports visible/always-on-top, bounds x=51, y=58, width=2456, height=1382, zoom about 1.279, and a 1920×1080 renderer viewport.

The initial DOM probe incorrectly matched only SVG labels containing `-Tier`. Its empty result was inconclusive because these relics use a named tier. The corrected structural probe measured three SVG badges, each about 127×33 CSS pixels, at x=896.5 and y=753.27, 849.30 and 945.34. Their ancestors had full viewport dimensions, visible styles and opacity 1; the badge rectangles were inside the viewport. The probe collected no account information or unrelated text.

After being asked specifically about brown “Inconsistent” labels near the center of each relic row, the owner confirmed: “Yes, I see Inconsistent labels.” These are genuine tier ratings from the enabled list. Named tiers are returned verbatim by the existing renderer, while one-letter tiers receive the `-Tier` suffix. The temporary diagnostic changed logging only, not badge styling, geometry, tier values or visibility gates.

## Boundaries and disposition

Static tracing found no later full-screen sibling covering ancient badges. Working card badges use an explicit composited layer/z-index; ancient anchors differ, but that difference is not a proven defect.

Ancient statistics requests remain denied by the controlled gateway. Tier display has an independent data path, so no network expansion is justified by this observation.

No speculative z-index, geometry or visibility patch is warranted by the confirmed result. Temporary instrumentation and copied vendor bundles are excluded from Git. Game progress, saves, Steam settings, the installed companion selection and the current PR branch remain unchanged. The current supervised diagnostic session may finish normally; the next normal launch selects the existing installed companion, not the temporary diagnostic.

Validation: temporary bundle syntax and signature checks passed, and source/payload comparisons allowed only the intended diagnostic ASAR change and outer signature resealing. The final repository delta is documentation only, checked with `git diff --check` and `python3 scripts/check_repository.py`; no test changes or full test rerun were needed. Other characters, starting events and display configurations remain outside this live observation.
