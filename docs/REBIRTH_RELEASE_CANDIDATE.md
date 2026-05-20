# Rebirth Release Candidate

## Status

Rebirth 011-020 moves the product from preview shell to final MVP release
candidate.

Implemented:

- Rebirth-native account registration/login/logout.
- SQLite persistence through Python stdlib.
- Account collection ownership.
- Account loadout save and match start integration.
- No-payment booster opening with persisted ownership.
- Progression, daily reward and tutorial completion persistence.
- Player profile and persisted achievement unlocks.
- CSRF protection for Rebirth mutations.
- Auth rate limiting and signed-in password changes.
- Finished Rebirth 021 starter card set with unique PNG art, tier-2 evolution
  truth and engine-backed abilities.
- Clash ability feedback, impact feel and match reward moment.
- Count-based collection/loadout editor with copy limits and curve preview.
- Defensive, aggressive and opportunist bot personalities.
- Deterministic Balance Lab with card, ability and profile impact.
- Release hygiene page and service worker cache bump.

Not implemented:

- Payment processor.
- Admin support tooling.
- Persisted live match state.
- Real multiplayer.

## Required Gate

```bash
python3 -m py_compile app.py services/rebirth_engine.py services/rebirth_cards.py services/rebirth_bot.py services/rebirth_state.py services/rebirth_match_store.py services/rebirth_product.py services/rebirth_persistence.py services/rebirth_balance.py
python3 -m pytest -q
node --check static/js/rebirth.js
node --check static/js/service-worker.js
node --check static/js/pwa.js
node --check static/js/rebirth_product.js
```

Current local result:

- `python3 -m pytest -q`: 61 passed
- Browser smoke: passed on desktop and mobile viewport with a temporary
  Rebirth database.

## Legacy Boundary

Retired browser routes still redirect to `/rebirth`. Retired API groups still
return `410 legacy_disabled`. No legacy economy, SQLAlchemy, SocketIO, Arena or
Ascension runtime was restored.
