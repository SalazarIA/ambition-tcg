# Rebirth Release Status

## Official Product State

Ambitionz Rebirth is the only active Ambitionz runtime product.

The active product is a Flask-served, vanilla-frontend, single-screen monster
duel with Rebirth-native auth, SQLite persistence, account collection, account
loadout, no-payment booster ownership, progression, onboarding, balance
simulation, player profile/achievements, match history, economy ledger,
support/admin tooling, auth hardening and release hygiene pages.

The active catalog now spans 100 cards (80 monsters across Fire/Water/Earth/
Shadow, 10 spells and 10 traps) with stable `ability_key` values, engine-backed
effects, server-authored clash feedback and balance telemetry.

The retired Arena, Ascension, BE2, SocketIO, economy, progression, shop,
collection and deck builder systems are not part of the runtime. Historical
tests live under `tests/legacy_disabled` and are intentionally excluded from
the release gate.

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
- `services/rebirth_monetization.py`
- `templates/index.html`
- `templates/rebirth.html`
- `templates/rebirth_product.html`
- `templates/_rebirth_global_nav.html`
- `static/css/rebirth.css`
- `static/js/rebirth.js`
- `static/js/rebirth_product.js`
- `static/js/rebirth_global.js`
- `static/js/pwa.js`
- `static/js/service-worker.js`
- `static/manifest.webmanifest`
- `static/assets/rebirth/manifest.json`
- `static/assets/rebirth/cards/*-art.png`
- `static/assets/rebirth/ui/*`

The active runtime language is **pt-BR**. UI strings, nav, modal and JS-rendered
copy use Portuguese. JSON API contracts and engine identifiers stay in English
so test fixtures and persistence remain stable.

## Active Browser Routes

- `GET /`
- `GET /rebirth`
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
- `POST /api/rebirth/attack`
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
- `POST /api/rebirth/admin/grant`

State-changing Rebirth APIs require `X-Rebirth-CSRF` by default. Auth endpoints
have a small in-memory rate limit. Password changes are available for signed-in
Rebirth users.

Retired API groups return JSON `410 legacy_disabled`:

- `/api/ascension/*`
- `/api/beta/*`
- `/api/booster/*`

## Gameplay Loop

Each match is a head-to-head duel with one persistent battlefield slot per side.
The contract is:

1. **MAIN_PHASE / phase=choose** — Player may evolve duplicates, summon a
   monster from hand (paying its mana cost), play a spell or arm a trap. Each
   action is a separate API call.
2. **COMBAT_PHASE** — After summoning, the player declares an attack with their
   battlefield monster. Combat resolves through the rules engine, comparing
   `effective_attack` (base + abilities). If the defender's `current_guard`
   reaches zero, it goes to the discard pile. With no defender, the attacker
   chips the opponent's HP directly.
3. **END_PHASE / phase=result** — Server records `last_clash`, ability events,
   damage and the `match_reward` payload (XP, level-up state, achievements,
   daily readiness). Player calls `next-turn` to advance.
4. **Next turn** — Both players refill their energy to `min(10, turn)`, draw to
   hand size and any surviving monsters become ready again.

Monsters are persistent on the field until destroyed. The "destroyed monsters
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
- support export/reset and admin token safety
- defeated-monster cleanup regression (engine destruction bug)
- mana curve playability (cheapest monster anchored in starter deck)

Current local result: `82 passed`.

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

Rebirth matches remain in memory with TTL expiry (default 3600s), max-entry cap
(default 512) and basic locking for threaded Gunicorn. Environment overrides:

- `REBIRTH_MATCH_TTL_SECONDS`
- `REBIRTH_MAX_MATCHES`

Rebirth account, collection, loadout, progression and booster ownership use
SQLite through Python stdlib. Match state itself remains in memory; live
in-progress matches are lost on process restart.

## Persistence

Default database path: `instance/rebirth.db`. Override via `REBIRTH_DB_PATH`.

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
- No database persistence for live in-progress match state.
- In-memory matches are lost on process restart or deploy.
- One starter collection per account.
- The active art manifest still covers only 13 of the 100 catalog cards
  with bespoke PNG art; remaining cards fall back to procedurally generated
  silhouettes.
- Browser screenshots are not committed as visual baselines yet.
- The 2019-line `static/js/rebirth.js` is still a single IIFE and would benefit
  from a future modularization pass.

## Next Steps

- Expand bespoke card art beyond the original 13 silhouettes.
- Modularize `static/js/rebirth.js` into testable units.
- Add screenshot-based visual QA baselines for desktop/mobile `/rebirth`.
- Tune defensive/opportunist bots and low-impact cards against
  `docs/REBIRTH_BALANCE_REPORT.md` plus real play sessions.
- Add real payment/economy only if a future product decision asks for it.
- Keep retired APIs and routes retired unless a future product decision says
  otherwise.
