# Starting-relic badge investigation

Status: diagnosis in progress on `codex/sts2-starting-relic-badges`, isolated from the current PR checkout. No compatibility repair has been established or installed.

## Confirmed evidence

The owner reports missing badges on the Neow starting-choice screen. Their earlier sighting at the right edge was the Untapped sidebar, not three relic ratings.

A temporary signed diagnostic copy, retaining the existing companion entitlements and controlled network boundary, confirms:

- Native layout identifies three choices: `SCROLL_BOXES`, `ARCANE_SCROLL`, and `PRECARIOUS_SHEARS`.
- The enabled genuine colorless/Regent lists cover those IDs. Their current rating is the named tier `Inconsistent`, not a letter-tier label.
- Renderer choices, tier mode and tier visibility are enabled; all three items have tier data. Room, submenu and obscuring-screen gates permit display.
- Normalized badge anchor positions resolve to x=50% and y=69.44%, 78.33%, 87.22% before the existing 3px offset.
- The diagnostic overlay window reports visible/always-on-top, bounds x=51, y=58, width=2456, height=1382, zoom about1.279, and a1920×1080 renderer viewport. These values alone do not establish actual visible paint or alignment.

The initial DOM probe incorrectly matched only SVG labels containing `-Tier`. Its empty result is inconclusive because these relics use a named tier. The corrected probe measures SVG badges structurally, without collecting account information or unrelated text.

## Boundaries and remaining work

Static tracing found no later full-screen sibling covering ancient badges. Working card badges use an explicit composited layer/z-index; ancient anchors differ, but that difference is not a proven defect.

Ancient statistics requests remain denied by the controlled gateway. Tier display has an independent data path, so no network expansion is justified by this observation.

Next: obtain corrected badge DOM rectangles and ancestor styles, reproduce the actual failure, then implement and verify the smallest repair. Temporary instrumentation and copied vendor bundles are excluded from Git. Game progress, saves, Steam settings, the installed companion selection and the current PR branch remain unchanged.
