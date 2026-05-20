# Ambitionz Rebirth Architecture

Ambitionz Rebirth is the active Ambitionz product surface. The current architecture is a Flask-served, JSON-driven, single-screen browser game with a pure Python rules engine and DOM-rendered HUD/game UI.

## Active Runtime Files

```text
app.py

services/rebirth_contracts.py
services/rebirth_cards.py
services/rebirth_art.py
services/rebirth_bot.py
services/rebirth_state.py
services/rebirth_serializers.py
services/rebirth_match_store.py
services/rebirth_engine.py
services/rebirth_product.py
services/rebirth_persistence.py
services/rebirth_balance.py

templates/index.html
templates/rebirth.html
templates/rebirth_product.html

static/css/rebirth.css
static/js/rebirth.js
static/js/rebirth_product.js
static/js/pwa.js
static/js/service-worker.js
static/manifest.webmanifest
static/assets/rebirth/manifest.json
static/assets/rebirth/cards/*
static/assets/rebirth/ui/*

tests/rebirth/*
```

The older `services/rebirth/` package is not part of the active Flask route or `/rebirth` product runtime. It remains repository history/legacy context only. Historical tests for retired systems live under `tests/legacy_disabled`.

## Backend Boundaries

- `app.py` owns Flask routes, request parsing, response formatting and HTTP status codes.
- `services/rebirth_contracts.py` owns phase constants, stable error codes and `RebirthError`.
- `services/rebirth_match_store.py` owns the active in-memory match store.
- `services/rebirth_cards.py` owns card catalog, lookup, deck construction and card instances.
- `services/rebirth_art.py` owns active card-art metadata, palette data and art paths.
- `services/rebirth_bot.py` owns bot response selection.
- `services/rebirth_state.py` owns match creation, draw helpers, hand/discard mutation and phase-neutral state helpers.
- `services/rebirth_engine.py` owns pure game rules: play card, compare attack, calculate damage, evolve duplicate, finish match and next turn.
- `services/rebirth_serializers.py` owns public JSON state, side payloads and card contract validation.
- `services/rebirth_product.py` owns Rebirth-native product shell payloads for
  auth, collection/loadout, booster, progression, onboarding, balance, desktop
  notes and release hygiene.
- `services/rebirth_persistence.py` owns SQLite schema creation, account
  creation/login, password hashing, account collection, loadout, progression,
  daily rewards, booster history and achievements.
- `services/rebirth_balance.py` owns deterministic local balance simulations
  and bot tuning summaries.

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
- `GET /rebirth/account`
- `GET /rebirth/collection`
- `GET /rebirth/shop`
- `GET /rebirth/progression`
- `GET /rebirth/profile`
- `GET /rebirth/desktop`
- `GET /rebirth/onboarding`
- `GET /rebirth/balance`
- `GET /rebirth/release`
- `POST /api/rebirth/start`
- `POST /api/rebirth/play-card`
- `POST /api/rebirth/evolve`
- `POST /api/rebirth/next-turn`
- `GET /api/rebirth/shell`
- `GET /api/rebirth/session`
- `GET /api/rebirth/csrf`
- `POST /api/rebirth/auth/register`
- `POST /api/rebirth/auth/login`
- `POST /api/rebirth/auth/logout`
- `POST /api/rebirth/auth/change-password`
- `GET /api/rebirth/auth-plan`
- `GET /api/rebirth/collection`
- `POST /api/rebirth/loadout`
- `GET /api/rebirth/shop`
- `POST /api/rebirth/booster/open`
- `GET /api/rebirth/progression`
- `GET /api/rebirth/profile`
- `POST /api/rebirth/progression/claim-daily`
- `GET /api/rebirth/desktop`
- `GET /api/rebirth/onboarding`
- `POST /api/rebirth/onboarding/complete`
- `GET /api/rebirth/balance/simulate`
- `GET /api/rebirth/release`

Collection, loadout, shop, booster, progression and tutorial routes persist to
Rebirth accounts. They do not restore the retired economy, old collection
system, old deck builder or legacy account stack.

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
- `auth_required`
- `auth_conflict`
- `invalid_credentials`
- `csrf_required`
- `rate_limited`
- `invalid_loadout`
- `reward_locked`

Expected player mistakes return JSON and do not return 500.

## Security Boundary

`app.py` adds minimum security headers on every response:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`
- a pragmatic CSP using local sources, with `unsafe-inline` only because the
  current templates and card rendering still use inline bootstrap data and
  inline styles.

`/service-worker.js` is served from the app root with `Service-Worker-Allowed: /`.

State-changing `/api/rebirth/*` routes require `X-Rebirth-CSRF` by default.
The token is stored in the Flask signed session and injected into Rebirth
templates. Register/login rotate the Rebirth session. Auth endpoints also use
a small in-memory rate limit for the current process.

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

`static/js/rebirth_product.js` is also framework-free. It binds account
register/login/logout, account loadout persistence, no-payment booster opening,
daily reward claiming, tutorial completion, password changes and balance reruns
on product-shell pages.

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
- `/static/assets/rebirth/cards/dreadmaw-art.png`
- `/static/assets/rebirth/cards/stoneshell-art.png`
- `/static/assets/rebirth/cards/stonewarden-art.png`
- `/static/assets/rebirth/cards/shadewisp-art.png`
- `/static/assets/rebirth/cards/skywarden-art.png`
- `/static/assets/rebirth/cards/stormwarden-art.png`
- `/static/assets/rebirth/cards/ironbastion-art.png`
- `/static/assets/rebirth/cards/ironbulwark-art.png`
- `/static/assets/rebirth/cards/embermaw-art.png`
- `/static/assets/rebirth/cards/embermaw-alpha-art.png`
- `/static/assets/rebirth/cards/voidstalker-art.png`
- `/static/assets/rebirth/cards/nightfang-art.png`
- `/static/assets/rebirth/ui/bot-card-back.png`
- `/static/assets/rebirth/ui/bot-emblem.png`

The service worker cache is versioned as `ambitionz-rebirth-final-mvp-v20` and lists only active Rebirth assets plus app shell essentials.

## Match Store

`services/rebirth_match_store.py` is intentionally in-memory for the MVP. It now
uses:

- TTL expiry, default `3600` seconds;
- max-entry trimming, default `512` matches;
- defensive cleanup on save/get/len/raw;
- basic locking around store operations for threaded Gunicorn.

It does not persist live match state. Account data uses the Rebirth SQLite
store below.

## Persistence Store

Rebirth uses SQLite through Python stdlib. Default path:

```text
instance/rebirth.db
```

Override:

- `REBIRTH_DB_PATH`

Tables:

- `users`
- `user_collection`
- `user_loadout`
- `user_progress`
- `reward_claims`
- `booster_history`
- `user_achievements`

The active store uses PBKDF2 password hashes and Flask signed session cookies.
It does not use SQLAlchemy, migrations from the retired app, or legacy account
models.

## Active Page Policy

- `/` is the Rebirth home and may scroll.
- `/rebirth` is the playable single-screen game and must not scroll.
- `/rebirth/account`, `/rebirth/collection`, `/rebirth/shop`,
  `/rebirth/progression`, `/rebirth/profile`, `/rebirth/desktop`,
  `/rebirth/onboarding`, `/rebirth/balance` and `/rebirth/release` are
  Rebirth-native product shell pages and may scroll.
- Legacy product routes redirect to `/rebirth` or return a safe retired API response.
- Active Rebirth pages do not load old Arena, BE2, Ascension, collection, progression, shop or economy CSS/JS.
- Historical tests are archived under `tests/legacy_disabled` and are not the active release gate.

## Validation Gates

Mandatory commands:

```bash
python3 -m py_compile app.py services/rebirth_engine.py services/rebirth_cards.py services/rebirth_bot.py services/rebirth_state.py services/rebirth_match_store.py services/rebirth_product.py services/rebirth_persistence.py services/rebirth_balance.py
python3 -m pytest -q
node --check static/js/rebirth.js
node --check static/js/service-worker.js
node --check static/js/pwa.js
node --check static/js/rebirth_product.js
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
