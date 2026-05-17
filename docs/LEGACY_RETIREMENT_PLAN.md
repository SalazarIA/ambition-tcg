# Legacy Retirement Plan

## Preserved Legacy

The old BE2 lane-based Arena remains available for fallback and internal validation:

- `templates/arena.html`
- `static/js/arena_clean_v48.js`
- `static/css/arena_clean_v48.css`
- BE2 services and socket systems
- `/training-legacy`
- `/arena`

These files are not deleted in this rebirth pass.

## Main Product

The main Training route is now Ascension Duel:

- `/training`
- `templates/arena_ascension.html`
- `static/js/ambitionz_ascension.js`
- `static/css/ambitionz_ascension.css`
- `/api/ascension/*`

## Migration Strategy

1. Keep old cards readable through collection and deck tools while Ascension cards become canonical for Training.
2. Use `migrate_legacy_card_to_ascension` for conservative card conversion.
3. Preserve economy, missions, profile, telemetry and feedback until their language and rewards are updated.
4. Move public copy to Ascension Duel terms first.
5. Later, migrate deck builder, collection filters and old card stats into Champion, Technique, Relic, Scheme and Ascension groupings.

## What Remains Legacy

- Lane targeting.
- Monster, Spell and Trap deck ratios.
- BE2 socket flow.
- Old Arena art and effects.
- Existing 3D arena renderer.

## What Becomes Canonical

- Ascension Duel engine.
- Ascension card catalog.
- Ambition Core.
- Mind Clash.
- One active Champion per side.
- `ax-` frontend surface.
