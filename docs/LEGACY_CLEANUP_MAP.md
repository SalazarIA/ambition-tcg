# Legacy Cleanup Map

## Rebirth Canonical Surface

- `/rebirth`
- `/api/rebirth/new`
- `/api/rebirth/decks`
- `/api/rebirth/decks/<deck_id>`
- `/api/rebirth/intent`
- `/api/rebirth/play-card`
- `/api/rebirth/resolve`
- `/api/rebirth/restart`
- `services/rebirth/*`
- `templates/rebirth.html`
- `static/css/rebirth.css`
- `static/js/rebirth.js`
- `static/js/rebirth_3d_adapter.js`
- `static/assets/rebirth3d/*`

## Legacy Surface

Routes found in `app.py` that remain compatibility or older beta surfaces:

- `/training` - Ascension beta training surface, now visually bridged to Rebirth.
- `/training-legacy` - old lane Arena fallback.
- `/arena` - authenticated old Arena route.
- `/collection` - original inventory collection surface.
- `/deck-builder` - original deck builder.
- `/shop` - gold-only beta shop.
- `/daily`
- `/missions`
- `/progression`
- `/roadmap` - public status page, now includes Rebirth migration bridge.
- `/tutorial` - Ascension tutorial surface.
- `/campaign`
- `/match-history`
- `/inventory`
- `/economy`

## Shared Surface

- `app.py`
- `templates/index.html`
- `templates/_legacy_rebirth_banner.html`
- `static/js/service-worker.js`
- `static/css/style.css`
- `static/css/ambitionz_ascension.css`
- `static/css/arena_clean_v48.css`
- global release/smoke tests in `tests/`
- QA scripts in `tools/qa/`

## Cleanup Rule

- Rebirth does not import legacy Arena JS/CSS.
- Rebirth does not use `az48` classes.
- Rebirth does not use old Socket.IO gameplay.
- Legacy files and routes are not removed until usage and migration are proven.
- Home prioritizes Rebirth.
- Old beta links are grouped under Legacy Access.
- Existing useful features should be migrated into Rebirth before retiring legacy surfaces.

## Current Cleanup Risk Notes

- `/arena` is authenticated and can redirect for anonymous users.
- `/collection`, `/deck-builder` and `/shop` may depend on account/economy state.
- `app.py` remains shared by Rebirth, Ascension and old Arena, so route edits must stay defensive.
- Service worker cache still carries legacy assets for offline fallback and compatibility.
