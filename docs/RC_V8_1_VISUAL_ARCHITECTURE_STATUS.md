# RC V8.1 Visual Architecture Status

## What Was Fixed

- Home now uses the Ascension `ax-` shell and visually matches Arena, Collection, Deck Builder, Chronicle, Roadmap and Tutorial.
- `/training` now has an explicit viewport contract and compact combat shell.
- Chronicle and reward details no longer push the core duel layout downward.
- Public navigation points to Ascension routes first.
- Service worker cache moved to `ambitionz-web-app-v194`.

## Home Rebirth

The first page now presents Ambitionz as Ascension Duel: one-card duel architecture, Champion progression, mind-game battle system and beta progression with no real-money payments. Primary CTAs are Play Ascension Duel, Collection and Deck Builder.

## Viewport Contract

The Arena uses `ax-arena-shell`, `ax-arena-viewport`, `ax-duel-altar-compact`, `ax-chronicle-compact`, `ax-internal-scroll` and `ax-action-compact`. Common desktop play should keep the core action flow inside one viewport.

## Compact Board Notes

Champion portraits, side readouts, Ambition Core, Intent controls, hand cards and action controls were reduced with clamp-based sizing. Secondary rite information uses details panels and the Chronicle scrolls internally.

## Product Surface Consistency

Collection, Deck Builder, Chronicle, Roadmap and Tutorial share the same background, topbar, panels, button treatment, card surfaces and typography tokens.

## QA Run

Expected validation:

- `python3 -m pytest -q`
- `python3 -m py_compile services/ascension_cards.py services/ascension_engine.py services/ascension_bot.py services/ascension_payloads.py services/ascension_progression.py services/ascension_taxonomy.py services/ascension_history.py`
- `node --check static/js/ambitionz_ascension.js`
- `node --check static/js/ambitionz_ascension_library.js`
- Ascension QA scripts, including viewport and product surface checks.

## Risks / Known Issues

- The viewport contract is static and CSS-driven; it should still be verified visually on target device classes before release.
- Real card art remains deferred to the local Ascension art pipeline.
- Legacy pages remain available and may still contain retired terminology by design.

## Next Recommended Blocks

- Add rendered screenshot regression checks for desktop and mobile.
- Add a route-level visual snapshot baseline for the Ascension shell.
- Continue balance tuning using `qa_ascension_balance_sim.py`.
