# Ambitionz Rebirth Architecture

Ambitionz Rebirth is the active Ambitionz product surface. The current architecture is a Flask-served, JSON-driven, single-screen browser game with a pure Python rules engine and DOM-rendered HUD/game UI.

## Active Runtime Files

```text
app.py

services/rebirth_contracts.py
services/rebirth_cards.py
services/rebirth_bot.py
services/rebirth_state.py
services/rebirth_serializers.py
services/rebirth_match_store.py
services/rebirth_engine.py

templates/index.html
templates/rebirth.html

static/css/rebirth.css
static/js/rebirth.js
static/js/pwa.js
static/js/service-worker.js
static/manifest.webmanifest
static/assets/rebirth/manifest.json
static/assets/rebirth/cards/*
static/assets/rebirth/ui/*

tests/test_rebirth_engine.py
tests/test_rebirth_routes.py
tests/test_rebirth_frontend_contract.py
tests/test_rebirth_home_promotion.py
```

The older `services/rebirth/` package is not part of the active Flask route or `/rebirth` product runtime. It remains repository history/legacy context only.

## Backend Boundaries

- `app.py` owns Flask routes, request parsing, response formatting and HTTP status codes.
- `services/rebirth_contracts.py` owns phase constants, stable error codes and `RebirthError`.
- `services/rebirth_match_store.py` owns the active in-memory match store.
- `services/rebirth_cards.py` owns card catalog, lookup, deck construction and card instances.
- `services/rebirth_bot.py` owns bot response selection.
- `services/rebirth_state.py` owns match creation, draw helpers, hand/discard mutation and phase-neutral state helpers.
- `services/rebirth_engine.py` owns pure game rules: play card, compare attack, calculate damage, evolve duplicate, finish match and next turn.
- `services/rebirth_serializers.py` owns public JSON state, side payloads and card contract validation.

Flask does not contain game rules. Browser JavaScript does not contain game rules. The simulation is the source of truth.

## State Machine

Valid phases:

- `choose`: player may select one hand card or combine an available duplicate.
- `result`: a clash has resolved; player may advance to the next turn.
- `finished`: match has a winner and only New Match is available.

Required public state fields:

- `match_id`
- `architecture`
- `turn`
- `phase`
- `player`
- `bot`
- `available_evolutions`
- `last_clash`
- `result`
- `winner`
- `is_finished`
- `log`

Required player/bot side concepts:

- `hp`
- `max_hp`
- `deck_count`
- `discard_count`
- `played_card`
- `wounded`
- player `hand`
- bot `hand_count`

## API Contract

Routes:

- `GET /health`
- `GET /`
- `GET /rebirth`
- `POST /api/rebirth/start`
- `POST /api/rebirth/play-card`
- `POST /api/rebirth/evolve`
- `POST /api/rebirth/next-turn`

Success:

```json
{
  "ok": true,
  "state": {},
  "result": null
}
```

Error:

```json
{
  "ok": false,
  "error": {
    "code": "stable_string_code",
    "message": "Human-readable message."
  }
}
```

Stable expected error codes:

- `missing_match`
- `invalid_phase`
- `missing_card`
- `invalid_card`
- `duplicate_not_available`
- `match_finished`
- `malformed_request`

Expected player mistakes return JSON and do not return 500.

## Frontend Runtime

`static/js/rebirth.js` is deliberately framework-free and split into internal modules:

- `RebirthApi`: fetch, JSON parsing and error normalization.
- `RebirthStore`: current state, selected card and pending state.
- `RebirthRenderer`: DOM rendering only.
- `RebirthInput`: button and hand events.
- `RebirthBoardScaler`: single-screen scaling and anti-scroll behavior.
- `RebirthAssets`: preload and fallback handling.
- `RebirthErrors`: non-breaking visual error messaging.

The frontend calls the JSON API, renders returned state and never computes gameplay outcomes.

## Single-Screen Board

`/rebirth` is a fixed cockpit, not a long page.

- Base board: `852px x 1846px`.
- Scale: `min(viewportWidth / 852, viewportHeight / 1846)`.
- Board is centered in the viewport.
- `html`, `body` and `.rb-game-viewport` do not document-scroll.
- Mouse wheel is prevented from moving the page.
- Touchmove outside approved micro-areas is prevented.

Allowed internal overflow is limited to controlled UI areas such as the hand/log if future density requires it.

## Active Asset Pipeline

Active manifest:

```text
static/assets/rebirth/manifest.json
```

Primary active assets:

- `/static/assets/rebirth/cards/dreadclaw-art.png`
- `/static/assets/rebirth/ui/bot-card-back.png`
- `/static/assets/rebirth/ui/bot-emblem.png`
- `/static/assets/rebirth/cards/stoneshell.svg`
- `/static/assets/rebirth/cards/shadewisp.svg`
- `/static/assets/rebirth/cards/skywarden.svg`
- `/static/assets/rebirth/cards/ironbastion.svg`
- `/static/assets/rebirth/cards/embermaw.svg`
- `/static/assets/rebirth/cards/voidstalker.svg`
- `/static/assets/rebirth/cards/nightfang.svg`

The service worker cache is versioned as `ambitionz-rebirth-single-screen-v4` and lists only active Rebirth assets plus app shell essentials.

## Active Page Policy

- `/` is the Rebirth home and may scroll.
- `/rebirth` is the playable single-screen game and must not scroll.
- Legacy product routes redirect to `/rebirth` or return a safe retired API response.
- Active Rebirth pages do not load old Arena, BE2, Ascension, collection, progression, shop or economy CSS/JS.

## Validation Gates

Mandatory commands:

```bash
python3 -m py_compile app.py services/rebirth_engine.py services/rebirth_cards.py services/rebirth_bot.py services/rebirth_state.py
python3 -m pytest -q
node --check static/js/rebirth.js
```

Rendered QA must verify:

- no vertical document scroll on `/rebirth`;
- no horizontal document scroll on `/rebirth`;
- wheel does not change `scrollY`;
- HUD, bot card, main card, duplicate panel, hand, CLASH, COMBINE, turn log and CTA are visible;
- no console errors;
- no page errors;
- no asset 404s;
- no native broken-image icons;
- core flow works: start -> combine -> clash -> next turn.
