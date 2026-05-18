# Ascension Viewport Contract

The `/training` route is the core product screen. On common desktop viewports, the player must be able to see opponent status, player status, active Champion stage, Intent controls, playable hand and Commit/Dominate controls without page scrolling.

## Desktop Contract

- `templates/arena_ascension.html` uses `ax-arena-shell` with `data-ax-viewport-contract`.
- The shell uses `100svh`, bounded grid rows and `overflow: hidden`.
- The main combat area is `ax-arena-viewport`.
- The Duel Altar is `ax-duel-altar-compact`.
- Chronicle and reward content sit in `ax-side-stack` and scroll internally.
- Hand cards are compact and horizontally scroll only within `ax-hand`.
- Actions use `ax-action-compact ax-reachable-actions`.

## Mobile Contract

Mobile can scroll when needed, but the action rail is sticky and the duel stage stays compact:

- No horizontal overflow.
- Champion panels compress to two columns.
- Chronicle has an internal max-height.
- Hand cards use horizontal scrolling.
- Commit, Dominate, New Duel and Tutorial controls remain reachable at the bottom.

## Regression Guard

`tools/qa/qa_ascension_viewport_contract.py` statically checks the shell, compact Duel Altar, internal Chronicle scroll, reachable actions, home shell and service worker cache version.
