# Ambitionz Rebirth

Ambitionz Rebirth is the active Ambitionz MVP: a fast, single-screen monster
duel where each side builds a three-slot battlefield and resolves direct,
tactile clashes through the Rebirth rules engine.

The previous Arena, Ascension and BE2 product surfaces are retired from the
active runtime. Rebirth-native campaign, economy, progression, shop,
collection and deck-building surfaces are part of the official product path.

## Active Stack

- Python
- Flask
- PostgreSQL persistence through the synchronous Rebirth repository
- Vanilla HTML/CSS/JavaScript as a renderer/input layer only
- PWA manifest and service worker
- PostgreSQL-authoritative authenticated match state with an in-process hot cache
- Command/event log on Rebirth match state with state hashes
- Deterministic replay envelope, canonical state hash and compressed snapshots
- Match history and economy ledger persisted for signed-in accounts
- 103-card catalog, including three Legendary cards, with WebP art, stable ability keys and engine-backed effects
- Real per-seed deck shuffling with playable-opener guarantee, one-time mulligan, summoning sickness with live keywords (RUSH/BURST/LIFESTEAL/TAUNT/SHIELD/PIERCE/REGEN/EXECUTE), context-aware traps, targeted damage spells and incremental fatigue instead of sudden-death exhaustion
- Defensive, aggressive and opportunist bot profiles
- Count-based loadout editor, match reward moments and deterministic Season 0 Balance Lab
- Self-service support export/reset and token-protected admin grants
- Gunicorn for deployment

The production runtime does not initialize SocketIO, async database loops,
legacy economy systems or the old multiplayer arena. PostgreSQL is the sole
production source of truth. SQLite is accepted only when `TESTING` is active
or `REBIRTH_ALLOW_SQLITE_TESTING=true` is explicitly supplied for isolated QA.
Gameplay authority is Python-first: rules, card effects, bot logic, balance
simulation, replay, telemetry analysis and economy decisions belong in Python;
browser code renders returned state and sends player intent.

## Active Routes

- `GET /` - Rebirth home
- `GET /rebirth` - playable Rebirth MVP
- `GET /rebirth/campaign` - ten-encounter PvE campaign
- `GET /rebirth/account` - Rebirth-native login/auth plan
- `GET /rebirth/collection` - collection and loadout preview
- `GET /rebirth/shop` - no-payment booster demo
- `GET /rebirth/progression` - progression and rewards preview
- `GET /rebirth/profile` - persisted player profile, achievements and account controls
- `GET /rebirth/history` - persisted match history and economy ledger
- `GET /rebirth/desktop` - desktop arena polish notes
- `GET /rebirth/onboarding` - onboarding/tutorial
- `GET /rebirth/balance` - balance and bot simulation
- `GET /rebirth/support` - account export/reset and admin safety notes
- `GET /rebirth/lab` - Rebirth Lab feature surface
- `GET /rebirth/release` - release candidate hygiene
- `GET /health` - deploy health JSON
- `GET /manifest.webmanifest`
- `GET /service-worker.js`

## Active APIs

- `POST /api/rebirth/start`
- `POST /api/rebirth/resume`
- `GET /api/rebirth/campaign`
- `POST /api/rebirth/campaign/start`
- `POST /api/rebirth/play-card`
- `POST /api/rebirth/attack`
- `POST /api/rebirth/evolve`
- `POST /api/rebirth/mulligan`
- `POST /api/labs/fusion`
- `POST /api/rebirth/next-turn`
- `GET /api/rebirth/shell`
- `GET /api/rebirth/session`
- `GET /api/rebirth/first-session`
- `GET /api/rebirth/csrf`
- `POST /api/rebirth/auth/register`
- `POST /api/rebirth/auth/login`
- `POST /api/rebirth/auth/logout`
- `POST /api/rebirth/auth/change-password`
- `GET /api/rebirth/auth-plan`
- `GET /api/rebirth/collection`
- `POST /api/rebirth/loadout`
- `GET /api/rebirth/shop`
- `GET /api/rebirth/market/offers`
- `POST /api/rebirth/market/list`
- `POST /api/rebirth/market/buy`
- `POST /api/rebirth/booster/open`
- `GET /api/rebirth/progression`
- `GET /api/rebirth/profile`
- `GET /api/rebirth/match-history`
- `GET /api/rebirth/match-history/<match_id>/events`
- `GET /api/rebirth/economy-ledger`
- `POST /api/rebirth/progression/claim-daily`
- `GET /api/rebirth/desktop`
- `GET /api/rebirth/onboarding`
- `POST /api/rebirth/onboarding/complete`
- `GET /api/rebirth/balance/simulate`
- `GET /api/rebirth/balance/telemetry`
- `GET /api/rebirth/content/validate`
- `GET /api/rebirth/async/share/<match_id>`
- `GET /api/rebirth/async/ghosts`
- `GET /api/rebirth/release`
- `GET /api/rebirth/support/export`
- `POST /api/rebirth/support/feedback`
- `POST /api/rebirth/support/reset`
- `POST /api/rebirth/support/delete-account`
- `POST /api/rebirth/admin/grant`
- `POST /api/rebirth/telemetry`
- `POST /api/rebirth/telemetry/beacon`
- `POST /api/rebirth/billing/checkout`
- `POST /api/rebirth/billing/webhook`

The Rebirth collection, shop and progression endpoints persist to Rebirth
accounts. Booster opening mutates signed-in ownership. Real-money Coinz/Gemas
purchase is disabled and its legacy verification endpoint returns
`410 monetization_disabled`.

`/api/rebirth/admin/grant` is disabled unless `REBIRTH_ADMIN_TOKEN` is configured
and the request sends the matching `X-Rebirth-Admin-Token` header.

State-changing Rebirth APIs use a session CSRF token by default. Auth endpoints
also have a small in-memory rate limit, and signed-in users can change their
password from the Rebirth profile page.

## Starter Card Set

Rebirth establishes an optimized browser card pipeline across the 103-card
current catalog.
Every active card now has:

- a WebP card image served on demand rather than preloading the full catalog;
- `ability_key`, `ability_name` and `ability_text` fields in the public card contract;
- a Rebirth engine effect covered by `tests/rebirth/test_rebirth_card_set.py`;
- a consistent evolution contract where evolved cards are tier 2 and are not in
  the default starter decks.

The foundation pool is `COMMON` and `UNCOMMON`; three `LEGENDARY` contracts
now provide signature chase cards with premium WebP references.

Retired browser routes such as `/arena`, `/training`, `/collection`,
`/deck-builder`, `/shop`, `/missions`, `/progression`,
`/tutorial`, `/profile`, `/inventory`, `/economy` and `/match-history` redirect to
`/rebirth`.

Retired API groups such as `/api/ascension/*`, `/api/beta/*` and
`/api/booster/*` return `410 legacy_disabled`.

## Current Gameplay Polish

The active game shell now surfaces card feel instead of hiding rules in text:
clash results include ability events, effective attack, impact feedback,
optional lightweight haptics/audio and a match reward payload. Signed-in players
see persisted XP, first-clash/first-win achievement moments and daily reward
readiness after a clash.

The collection page uses a count-based eight-card loadout editor with copy
limits, attack/guard totals and duplicate-pair preview. The Balance page runs
deterministic simulations across defensive, aggressive and opportunist bot
profiles and reports per-card/per-ability impact.

## Run Locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export REBIRTH_DATABASE_URL='postgresql://user:password@localhost:5432/ambitionz'
python -m services.rebirth_schema upgrade
python app.py
```

Open:

```text
http://127.0.0.1:8080/
http://127.0.0.1:8080/rebirth
```

## Test

Use the project venv interpreter (`.venv/bin/python`) explicitly. Running
the suite through the system `python3` masks real failures when the global
interpreter lacks `psycopg`, `pytest-asyncio` or other dev deps. The studio
audit P2 logs an example: `python3 -m pytest -q` reports 5 failures from
`ModuleNotFoundError: No module named 'psycopg'`; the same command via
`.venv/bin/python -m pytest -q` finishes with **1202 passed, 0 skipped**.

```bash
pip install -r requirements-dev.txt
.venv/bin/python -m py_compile app.py services/rebirth_engine.py services/rebirth_cards.py services/rebirth_bot.py services/rebirth_state.py services/rebirth_match_store.py services/rebirth_product.py services/rebirth_persistence.py services/rebirth_balance.py
.venv/bin/python -m pytest -q                             # fast suite — 1202 passed
.venv/bin/python -m pytest tests/rebirth/concurrency -q   # Postgres (local binary OR Docker, ver tests/rebirth/concurrency/availability.py)
.venv/bin/python -m pytest tests/rebirth -m e2e -q        # Playwright + Chromium
.venv/bin/python -m pytest -m "" -q                       # tudo de uma vez — 1221 passed
.venv/bin/python tools/rebirth_balance_report.py --matches 120 --output docs/REBIRTH_BALANCE_REPORT.md
node --check static/js/rebirth.js
node --check static/js/service-worker.js
node --check static/js/pwa.js
node --check static/js/rebirth_product.js
node tests/js/test_rebirth_audio_chain_dedup.cjs
```

> Os testes de concurrency exigem PostgreSQL 15+ disponível localmente
> (`brew install postgresql@15`) ou Docker rodando. A fixture descobre
> qualquer dos dois automaticamente; ver
> [tests/rebirth/concurrency/availability.py](tests/rebirth/concurrency/availability.py).

The standard pytest suite is scoped to `tests/rebirth` through `pytest.ini`.
Tests for the retired pre-Rebirth product are preserved under
`tests/legacy_disabled` and are not authoritative for the active product.

## Development Tools

Runtime dependencies stay intentionally small in `requirements.txt`. Development
and local tooling dependencies live in `requirements-dev.txt`; this includes
pytest, Pillow for the local card-art pipeline and Playwright for optional QA
scripts.

The production deploy runs `python -m services.rebirth_schema upgrade` before
Gunicorn starts; `/health` rejects traffic with `503` when the migrated
PostgreSQL schema is missing or unhealthy. See
`docs/AAA_FOUNDATION_V58.md` for rollout and rollback gates.

## Historical Docs

Some older documentation still describes Arena, Ascension, BE2, economy,
progression or SocketIO-era work. Treat those files as historical unless a
current Rebirth status document says otherwise. The current source of truth is:

- `docs/REBIRTH_RELEASE_STATUS.md`
- `docs/REBIRTH_AAA_GAME_STUDIO_ROADMAP.md`
- `docs/REBIRTH_ARCHITECTURE.md`
- `docs/REBIRTH_V60_V65_ENGINE_CONTRACT.md`
- `docs/REBIRTH_CARD_SET_STATUS.md`
- `docs/LEGACY_REMOVAL_REPORT.md`
- `docs/REBIRTH_REBUILD_REPORT.md`
