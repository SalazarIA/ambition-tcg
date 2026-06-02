# Rebirth Release Status

> Updated for the closed-beta hardening pass on 2026-06-01. Operational
> persistence, asset and mobile guidance is also defined in
> `docs/AAA_FOUNDATION_V58.md`.

## Official Product State

Ambitionz Rebirth is the only active Ambitionz runtime product.

The active product is a Flask-served, vanilla-frontend, three-slot monster
duel with a ten-node PvE campaign, Rebirth-native auth, PostgreSQL persistence, account collection, account
loadout, no-payment booster ownership, progression, onboarding, beta retention quests, balance
simulation, player profile/achievements, match history, economy ledger,
support/admin tooling, self-service export/deletion, consent-gated signup, auth hardening and release hygiene pages.

The active catalog spans 103 cards (83 monsters, 10 spells and 10 traps),
including three Legendary contracts, with stable `ability_key` values,
engine-backed effects, server-authored clash feedback and balance telemetry.

The retired Arena, Ascension, BE2 and SocketIO systems are not part of the
runtime. Rebirth-native economy, progression, shop, collection and deck
builder surfaces are active. Historical tests live under
`tests/legacy_disabled` and are intentionally excluded from the release gate.

## Active Runtime

- `app.py`
- `services/rebirth_contracts.py`
- `services/rebirth_cards.py`
- `services/rebirth_art.py`
- `services/rebirth_bot.py`
- `services/rebirth_state.py`
- `services/rebirth_events.py`
- `services/rebirth_serializers.py`
- `services/rebirth_match_store.py`
- `services/rebirth_engine.py`
- `services/rebirth_product.py`
- `services/rebirth_persistence.py`
- `services/rebirth_balance.py`
- `services/rebirth_schema.py`
- `services/rebirth_campaign.py`
- `templates/index.html`
- `templates/rebirth.html`
- `templates/rebirth_campaign.html`
- `templates/rebirth_product.html`
- `templates/_rebirth_global_nav.html`
- `static/css/rebirth.css`
- `static/js/rebirth.js`
- `static/js/rebirth_ui.js`
- `static/js/rebirth_campaign.js`
- `static/js/rebirth_boss_fx.js`
- `static/js/rebirth_product.js`
- `static/js/rebirth_global.js`
- `static/js/pwa.js`
- `static/js/service-worker.js`
- `static/manifest.webmanifest`
- `static/assets/rebirth/manifest.json`
- `static/assets/rebirth/cards/*-art.webp`
- `static/assets/rebirth/ui/*`

The active runtime language is **pt-BR**. UI strings, nav, modal and JS-rendered
copy use Portuguese. JSON API contracts and engine identifiers stay in English
so test fixtures and persistence remain stable.

## Active Browser Routes

- `GET /`
- `GET /rebirth`
- `GET /rebirth/campaign`
- `GET /rebirth/account`
- `GET /rebirth/collection`
- `GET /rebirth/shop`
- `GET /rebirth/progression`
- `GET /rebirth/profile`
- `GET /rebirth/history`
- `GET /rebirth/desktop`
- `GET /rebirth/onboarding`
- `GET /rebirth/balance`
- `GET /rebirth/support`
- `GET /rebirth/lab`
- `GET /rebirth/release`
- `GET /health`
- `GET /manifest.webmanifest`
- `GET /service-worker.js`

Retired browser routes redirect to `/rebirth`; examples include `/arena`,
`/training`, `/training-legacy`, `/collection`, `/deck-builder`, `/shop`,
`/ranking`, `/leaderboard`, `/missions`, `/progression`,
`/tutorial`, `/profile`, `/how-to-play`, `/inventory`, `/economy` and
`/match-history`.

## Active APIs

- `POST /api/rebirth/start`
- `GET /api/rebirth/campaign`
- `POST /api/rebirth/campaign/start`
- `POST /api/rebirth/play-card`
- `POST /api/rebirth/attack`
- `POST /api/rebirth/evolve`
- `POST /api/labs/fusion`
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
- `GET /api/rebirth/release`
- `GET /api/rebirth/support/export`
- `POST /api/rebirth/support/reset`
- `POST /api/rebirth/support/delete-account`
- `POST /api/rebirth/admin/grant`
- `POST /api/rebirth/telemetry`

State-changing Rebirth APIs require `X-Rebirth-CSRF` by default. Auth endpoints
have a small in-memory rate limit. Password changes are available for signed-in
Rebirth users.

Retired API groups return JSON `410 legacy_disabled`:

- `/api/ascension/*`
- `/api/beta/*`
- `/api/booster/*`

## Gameplay Loop

Each match is a head-to-head duel with three persistent battlefield slots per side.
The contract is:

1. **MAIN_PHASE / phase=choose** — Player may evolve duplicates, summon a
   monster from hand (paying its mana cost), play a spell, arm a trap, evolve
   duplicates from hand or fuse adjacent matching field monsters. Each action
   is an authoritative command and a separate API call.
2. **COMBAT_PHASE** — After summoning, the player declares an attack with their
   battlefield monster. Combat resolves through the rules engine, comparing
   `effective_attack` (base + abilities). If the defender's `current_guard`
   reaches zero, it goes to the discard pile. With no defender, the attacker
   chips the opponent's HP directly.
3. **END_PHASE / phase=result** — Server records `last_clash`, ability events,
   damage and the `match_reward` payload (XP, level-up state, achievements,
   daily readiness). Player calls `next-turn` to advance.
4. **Next turn** — Both players refill their energy to
   `min(10, max(2, turn))`, draw to hand size and any surviving monsters become
   ready again.

Monsters are persistent on the field until destroyed or consumed by fusion. The "destroyed monsters
linger on the field" bug from earlier releases is fixed by clearing
`side["battlefield"]` of defeated cards before re-syncing the slot view.

## Mana Curve

Monster cost scales with the card's total stats so the energy ramp is
meaningful. Tier-1 monsters cost 1 to 4 mana; evolved monsters cost the base
plus one. Spells and traps stay at 1 to 3 mana. Energy advances from 1 to 10
across turns, mirroring the Hearthstone curve.

The starter deck anchors on the cheapest available monster so opening hands
always contain a turn-1 playable card.

## Tests

The authoritative suite is `tests/rebirth`. `pytest.ini` uses `testpaths =
tests/rebirth` so `python3 -m pytest -q` runs the active Rebirth product suite.

Current Rebirth coverage includes:

- Rebirth route smoke and visual contract assertions
- Rebirth JSON API start/evolve/play/attack/next-turn contracts
- retired browser route redirect behavior
- retired API `410 legacy_disabled` behavior
- frontend template/CSS/JS/service-worker asset contract (pt-BR strings)
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
- age/privacy consent, authenticated support export and permanent account deletion
- Rebirth card set art/manifest truth, tier-2 evolution contract and
  engine-backed abilities
- bot personality contracts for defensive, aggressive and opportunist profiles
- clash feel contract for ability events, visual impact and match reward payloads
- count-based collection/loadout editor contract
- balance lab reports for card, ability and bot-profile impact
- command/event/state hash contract for active matches
- persisted match history and event replay source data
- economy ledger entries for starter cards, match XP, boosters, daily rewards,
  tutorial XP and admin grants
- support export/reset/delete and admin token safety
- defeated-monster cleanup regression (engine destruction bug)
- mana curve playability (cheapest monster anchored in starter deck)
- campaign unlock/reward/idempotency and boss presentation contracts
- Labs field-fusion persistence and deterministic replay coverage

Current verification is reported per roadmap pass; use `python3 -m pytest -q
tests/rebirth` and explicitly run `-m e2e` before release.

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

Authenticated Rebirth matches are persisted with public and authoritative
runtime state in PostgreSQL. An in-process hot cache retains TTL expiry
(default 3600s), max-entry cap (default 512) and basic locking for threaded
Gunicorn; a cache miss rehydrates from PostgreSQL. Environment overrides:

- `REBIRTH_MATCH_TTL_SECONDS`
- `REBIRTH_MAX_MATCHES`

Rebirth account, collection, loadout, progression, booster ownership, ledgers
and authenticated match state use synchronous PostgreSQL persistence.

## Persistence

Production requires `REBIRTH_DATABASE_URL` (or `DATABASE_URL`) and applies
`python -m services.rebirth_schema upgrade` before process startup. SQLite is
available only to explicitly isolated automated tests.

Persisted tables:

- `users`
- `user_collection`
- `user_loadout`
- `user_progress`
- `reward_claims`
- `booster_history`
- `user_achievements`
- `match_history`
- `match_commands`
- `match_events`
- `economy_ledger`
- `admin_audit_log`

Passwords are hashed with PBKDF2. Flask session cookies use HttpOnly and
SameSite defaults, Rebirth mutations use a session CSRF token, and auth
endpoints have a small in-memory throttle. The runtime still does not use
SQLAlchemy or legacy database models.

Signed-in match snapshots are copied into `match_history`, `match_commands` and
`match_events`. Live in-progress match objects still use the in-memory match
store; this is not yet a durable reconnect system.

`economy_ledger` records movement reasons and balances for XP and card grants.
There is no payment processor and no retired economy runtime.

## Current Limitations

- No real multiplayer.
- No payment processor.
- Admin grant support is MVP-only and requires `REBIRTH_ADMIN_TOKEN`.
- Authenticated live in-progress match snapshots are recoverable from persisted
  runtime state; guest in-progress matches remain memory-only.
- One starter collection per account.
- The current asset directory exposes premium bespoke art for selected cards;
  remaining catalog entries use optimized WebP deck art paths.
- Browser screenshots are not committed as visual baselines yet.
- The 3197-line `static/js/rebirth.js` is still a single IIFE and would benefit
  from a future modularization pass.
- Current deterministic health checks still flag long matches, chain
  readability and a large bot-profile difficulty spread.

## Next Steps

- Expand bespoke card art beyond the original 13 silhouettes.
- Modularize `static/js/rebirth.js` into testable units.
- Add screenshot-based visual QA baselines for desktop/mobile `/rebirth`.
- Tune the aggressive difficulty spike, long-match pacing and low-impact cards against
  `docs/REBIRTH_BALANCE_REPORT.md` plus real play sessions.
- Add real payment/economy only if a future product decision asks for it.
- Keep retired APIs and routes retired unless a future product decision says
  otherwise.
