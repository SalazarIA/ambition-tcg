# Rebirth Release Status

## Official Product State

Ambitionz Rebirth is the only active Ambitionz runtime product.

The active product is a Flask-served, vanilla frontend, single-screen monster
duel MVP with Rebirth-native auth, SQLite persistence, account collection,
account loadout, no-payment booster ownership, progression, onboarding, balance
simulation, player profile/achievements, auth hardening and release hygiene
pages. The old Arena, Ascension, BE2, SocketIO,
economy, progression, shop, collection and deck builder systems are retired from
runtime and must not be restored just to satisfy historical tests.

## Active Runtime

- `app.py`
- `services/rebirth_contracts.py`
- `services/rebirth_cards.py`
- `services/rebirth_art.py`
- `services/rebirth_bot.py`
- `services/rebirth_state.py`
- `services/rebirth_serializers.py`
- `services/rebirth_match_store.py`
- `services/rebirth_engine.py`
- `services/rebirth_product.py`
- `services/rebirth_persistence.py`
- `services/rebirth_balance.py`
- `templates/index.html`
- `templates/rebirth.html`
- `templates/rebirth_product.html`
- `static/css/rebirth.css`
- `static/js/rebirth.js`
- `static/js/rebirth_product.js`
- `static/js/pwa.js`
- `static/js/service-worker.js`
- `static/manifest.webmanifest`
- `static/assets/rebirth/manifest.json`
- `static/assets/rebirth/cards/*-art.png`
- `static/assets/rebirth/ui/*`

## Active Browser Routes

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
- `GET /health`
- `GET /manifest.webmanifest`
- `GET /service-worker.js`

Retired browser routes redirect to `/rebirth`; examples include `/arena`,
`/training`, `/training-legacy`, `/collection`, `/deck-builder`, `/shop`,
`/ranking`, `/leaderboard`, `/missions`, `/progression`, `/campaign`,
`/tutorial`, `/profile`, `/how-to-play`, `/inventory`, `/economy` and
`/match-history`.

## Active APIs

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

The collection, loadout, shop, booster and progression APIs now persist to
Rebirth accounts. Booster opening mutates signed-in ownership, but no payment
processor or retired economy runtime is active.

State-changing Rebirth APIs are guarded by a session CSRF token by default.
Auth endpoints use a small in-memory throttle. Password changes are available
for signed-in Rebirth users.

Retired API groups return JSON `410 legacy_disabled`:

- `/api/ascension/*`
- `/api/beta/*`
- `/api/booster/*`

## Tests

The authoritative suite is `tests/rebirth`.

`pytest.ini` uses `testpaths = tests/rebirth` so `python3 -m pytest -q` runs the
active Rebirth product suite. Historical tests for the retired pre-Rebirth
product are preserved under `tests/legacy_disabled` with a README and collection
guard explaining why they are not part of the release gate.

Current Rebirth suite coverage includes:

- Rebirth route smoke
- Rebirth JSON API start/evolve/play/next-turn contracts
- retired browser route redirect behavior
- retired API `410 legacy_disabled` behavior
- frontend template/CSS/JS/service-worker asset contract
- security headers on public surfaces
- in-memory match store save/get/expiry/cleanup/max-limit behavior
- product shell routes and Rebirth-native preview APIs
- collection loadout validation and no-payment booster demo
- register/login/logout/session persistence
- CSRF protection, auth rate limiting and password change behavior
- account-owned collection, loadout, booster history and progression
- player profile and persisted achievement unlocks
- tutorial completion and daily reward persistence
- deterministic balance simulation and release route contracts

Current local result for this block:

```text
51 passed
```

Browser QA also passed on a temporary local database for account registration,
booster ownership, clash progression, tutorial completion, daily reward,
profile achievements, balance rerun, release page, and mobile `390x844`
rendering.

Do not reuse old historical counts such as `242 passed`; they described a
different product surface.

## Security Headers

The Flask app applies minimum headers to all responses:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`
- a pragmatic local-only CSP compatible with current inline template styles and
  bootstrap data.

`/service-worker.js` also declares `Service-Worker-Allowed: /`.

## Match Store

Rebirth matches remain in memory. The store now includes:

- TTL-based expiry, default `3600` seconds;
- defensive cleanup on save/get/len/raw;
- max-entry cap, default `512`;
- basic locking around store operations for threaded Gunicorn.

Environment overrides:

- `REBIRTH_MATCH_TTL_SECONDS`
- `REBIRTH_MAX_MATCHES`

Rebirth account, collection, loadout, progression and booster ownership now use
SQLite through Python stdlib. Match state itself remains in memory.

## Persistence

Default database path:

```text
instance/rebirth.db
```

Environment override:

- `REBIRTH_DB_PATH`

Persisted Rebirth tables:

- `users`
- `user_collection`
- `user_loadout`
- `user_progress`
- `reward_claims`
- `booster_history`
- `user_achievements`

Passwords are hashed with PBKDF2. Flask session cookies use HttpOnly and
SameSite defaults, Rebirth mutations use a session CSRF token, and auth
endpoints have a small in-memory throttle. The runtime still does not use
SQLAlchemy or legacy database models.

## Active Assets

The active Rebirth art manifest is:

```text
static/assets/rebirth/manifest.json
```

It lists 13 active monster PNG assets:

- `dreadclaw-art.png`
- `dreadmaw-art.png`
- `stoneshell-art.png`
- `stonewarden-art.png`
- `shadewisp-art.png`
- `skywarden-art.png`
- `stormwarden-art.png`
- `ironbastion-art.png`
- `ironbulwark-art.png`
- `embermaw-art.png`
- `embermaw-alpha-art.png`
- `voidstalker-art.png`
- `nightfang-art.png`

The active service worker cache is `ambitionz-rebirth-final-mvp-v20` and
does not cache Arena or Ascension assets.

## Current Limitations

- No real multiplayer.
- No payment processor.
- No admin tools for account support yet.
- No database persistence for live in-progress match state.
- In-memory matches are lost on process restart or deploy.
- Rebirth has one starter collection and deterministic bot behavior.
- Screenshot baselines are not committed yet.
- Historical docs and archived tests may describe retired systems; current
  Rebirth docs are authoritative.

## Next Steps

- Add admin/support tooling for account reset and collection inspection.
- Add screenshot-based visual QA baselines for desktop/mobile `/rebirth`.
- Add real payment/economy only if a future product decision asks for it.
- Migrate only useful old-product ideas into Rebirth-native contracts.
- Keep retired APIs and routes retired unless a future product decision says
  otherwise.
