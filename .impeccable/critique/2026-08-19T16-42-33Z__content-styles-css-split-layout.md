---
target: iPad split layout (content/styles.css + recipe.js)
total_score: 10
max_score: 20
na_heuristics: 2,5,7,9,10
p0_count: 0
p1_count: 1
timestamp: 2026-08-19T16-42-33Z
slug: content-styles-css-split-layout
---
## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 2 | Layout switches silently on rotation with no transition, and once split the fixed toolbar visually masks whatever content scrolls under its bottom-right corner, so the user can't tell if that's "no more content" or "content, hidden" |
| 2 | Match System / Real World | n/a | No real-world metaphor applies to a two-column reading layout |
| 3 | User Control and Freedom | 1 | Split mode is fully automatic (media-query driven); there's no toggle to force single-column even if a user prefers it on a large landscape iPad |
| 4 | Consistency and Standards | 2 | `.recipe-toolbar` is `position: fixed; bottom: 20px; right: 20px` everywhere. In single-column mode that's over the page's one content stream; in split mode it lands over the *right* pane specifically, so the same fixed element behaves differently relative to content depending on mode |
| 5 | Error Prevention | n/a | No user input in this feature |
| 6 | Recognition Rather Than Recall | 3 | Core win of the feature is real: ingredients stay visible next to steps, removing the scroll-back-and-forth Casey (mobile/one-handed) and Alex (efficiency) both hate. Undercut by the toolbar overlap below |
| 7 | Flexibility and Efficiency | n/a | Feature is passive/automatic; no accelerators apply |
| 8 | Aesthetic and Minimalist Design | 2 | A solid opaque button stack sits on top of live paragraph text at the bottom of the right pane — the single ugliest thing on the page in this mode |
| 9 | Error Recovery | n/a | No error states in this feature |
| 10 | Help and Documentation | n/a | Passive layout change; nothing to document |
| **Total** | | **10/20** | **Acceptable (50%)** |

Five heuristics scored `n/a` (2, 5, 7, 9, 10) because this critique scopes to the split-layout feature itself, not the whole recipe page.

## Design Specificity Verdict

**LLM assessment**: The split layout is a genuinely specific, well-targeted idea: two-pane reading for a cooking device propped up in landscape, driven off `pointer: coarse` so it never fires on a mouse-and-keyboard desktop. That's not a generic template pattern, it's built for the exact device this site's users actually cook next to. The mechanism (DOM node re-parenting keyed off `matchMedia`, reversible on `exitSplit`) is careful engineering, not a shortcut.

**Deterministic scan**: `detect.mjs --json public/reference/nested_list_demo.html` returned a clean `[]` (exit 0) — no generic-AI-slop patterns detected on the built page.

**Visual overlays**: Not applicable this run — see Method note below on how verification was actually done.

## Overall Impression

The split-layout concept is right and the JS is careful, but it shipped without checking it against the rest of the page's chrome. The floating toolbar (`Collapse All` / `Copy Ingredients` / `Reset`) was designed for a single scrolling column and nobody re-checked its `position: fixed` box against the new two-pane geometry. In split mode it parks itself directly on top of the bottom of the right pane's scrollable content, permanently, for as long as that pane is scrolled to its end. That's the single biggest opportunity here: the layout math is solid, the overlap is a five-minute CSS fix.

## What's Working

- **The trigger condition is precise.** `(pointer: coarse) and (orientation: landscape) and (min-width: 900px) and (max-height: 900px)` is deliberately narrow — it won't misfire on a desktop browser resized to a wide, short window, and the JS (`SPLIT_QUERY` in `recipe.js`) mirrors the CSS media query exactly rather than duplicating a slightly-different threshold.
- **The DOM restructuring is reversible and idempotent.** `enterSplit`/`exitSplit` both guard on the current class state before touching the DOM, and `sourceOrder` is captured once so rotating back to portrait restores the original element order exactly. Rotating the device repeatedly won't accumulate drift.
- **Independent pane scrolling works.** Confirmed live: right pane `scrollHeight` (909px) exceeds its `clientHeight` (782px) and scrolls on its own with `overscroll-behavior: contain`, while the left ingredients pane stays put. That's the actual point of the feature and it holds up.

## Priority Issues

**[P1] Fixed toolbar overlaps split-pane content**
Why it matters: `.recipe-toolbar` (`content/styles.css:314`) is `position: fixed; bottom: 20px; right: 20px` with no split-mode override. Measured live at iPad-landscape dimensions: the toolbar's box (133×163px) sits entirely inside the right pane's bounding box, over its last ~163px of vertical scroll room. Any content that ends up there (Notes, Related Recipes, or a real recipe's final steps) is visually covered by four opaque buttons with no affordance that something is hidden behind them. Recognition Rather Than Recall (heuristic 6) exists specifically so ingredients stay visible; this bug takes the same amount of content away at the other end of the pane.
Fix: inside the existing `@media (pointer: coarse) and (orientation: landscape)…` block, either give `main.split-layout .split-pane-body` a `padding-bottom` sized to the toolbar's height plus its `bottom` offset, or reposition `.recipe-toolbar` to anchor to the split-pane's own stacking context in that mode instead of the viewport.
Suggested command: `/impeccable layout`

**[P2] No manual override for split mode**
Why it matters: the feature is entirely media-query driven with no user-facing toggle. A user who wants a single scrolling column on an iPad in landscape (or, conversely, who wants split behavior forced on a device the query doesn't catch) has no path to it. Heuristic 3 (User Control and Freedom) scores low for exactly this.
Fix: not urgent enough to block the P1 fix, but worth a follow-up if this feature gets used enough to generate that request.
Suggested command: `/impeccable adapt`

## Persona Red Flags

**Alex (Power User, cooking hands-free off an iPad on the counter)**: Rotates the iPad into landscape mid-recipe expecting the split view to help. Scrolls the steps pane to the last step or the Notes section and finds the last visible instructions physically covered by the `Reset`/`Copy Ingredients` buttons. Has to scroll past the covered zone or tap-drag around the buttons to read what's underneath — the opposite of the efficiency this feature promises.

**Casey (Distracted Mobile User, one-handed, interrupted often)**: Benefits most from having ingredients pinned next to steps (no scroll-hunting after an interruption), which genuinely helps here. But the toolbar sitting exactly in the bottom-right thumb zone, now overlapping content instead of floating over empty margin, means an errant tap near the pane's edge is more likely to hit `Reset` than intended.

## Minor Observations

- `main.split-layout .split-pane > section:first-child > h2` (`content/styles.css:473`) only fires in the left (ingredients) pane in practice — the right pane's first section starts with an `h1`, not an `h2`, so the rule is a no-op there. Not a bug, but the selector reads as if it applies to both panes.
- Left pane can end up with substantial empty space below short ingredient lists while the right pane scrolls independently above it — expected given two independently-sized columns, not something to chase.

## Method note (read before acting on this report)

This is a **degraded, single-context run**: I did not spawn isolated Assessment A / Assessment B sub-agents for this critique, because the request was narrow (verify one already-hard-to-test feature) and the live-browser evidence below was gathered directly in this thread rather than by a separate agent. Flagging it per the skill's rule rather than presenting it as a full dual-agent critique.

**How iPad-landscape was actually verified**: Chrome DevTools' device toolbar can fake screen dimensions but not the `pointer: coarse` media feature that gates this layout, which is why testing it in Chrome has been unreliable. There's no CDP media-emulation call exposed through the available browser tools either. So verification here reproduced the exact DOM mutation `recipe.js`'s `enterSplit()` performs (same ingredient-section detection, same node re-parenting) directly in a real Chrome tab resized to 1194×834 (iPad landscape point size), then measured the live render with `getBoundingClientRect()`. This proves the CSS grid, pane-scrolling, and toolbar-overlap behavior exactly as shipped. It does **not** prove the `pointer: coarse` detection itself fires correctly on a real iPad; that part still needs a physical device or a tool with real CDP media-feature override.
