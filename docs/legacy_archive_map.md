# Legacy Archive Map

This map documents old Ambitionz areas that are intentionally isolated from the active Rebirth product.

## Inactive Legacy Areas

- `game/`: old card, bot, battle, deck, progression and reward logic.
- `routes/`: old auth, admin and public route modules.
- `sockets/`: old Socket.io gameplay runtime.
- `services/arena_*`: old arena payload and command services.
- `services/battle_engine_v2*`: old BE2 logic and adapters.
- `services/ascension_*`: old Ascension prototype services.
- `services/economy/` and `services/economy_service.py`: old inventory, ownership and currency systems.
- `templates/arena*.html`, `templates/collection*.html`, `templates/deck_builder*.html`, `templates/shop.html`, `templates/missions.html`, `templates/progression.html`, `templates/ranking.html`, `templates/leaderboard.html`: old UI surfaces.
- `static/css/ambitionz_*.css`, `static/css/arena*.css`, `static/css/style.css`: old visual system.
- `static/js/ambitionz_*.js`, `static/js/arena*.js`, `static/js/deck_builder*.js`, `static/js/booster_opening.js`: old client systems.
- `tests/legacy_disabled/`: old product tests preserved outside the active release gate.

## Active Rebirth Files

- `app.py`
- `services/rebirth_contracts.py`
- `services/rebirth_cards.py`
- `services/rebirth_art.py`
- `services/rebirth_state.py`
- `services/rebirth_serializers.py`
- `services/rebirth_match_store.py`
- `services/rebirth_bot.py`
- `services/rebirth_engine.py`
- `templates/index.html`
- `templates/rebirth.html`
- `static/css/rebirth.css`
- `static/js/rebirth.js`
- `static/js/pwa.js`
- `static/js/service-worker.js`
- `static/manifest.webmanifest`
- `tests/rebirth/*`
