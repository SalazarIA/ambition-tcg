# Rebirth Release Status

> Updated for the AAA studio-foundation pass on 2026-06-02. Operational
> persistence, asset and mobile guidance is also defined in
> `docs/AAA_FOUNDATION_V58.md`.

## Official Product State

Ambitionz Rebirth is the only active Ambitionz runtime product.
The forward studio roadmap is `docs/REBIRTH_AAA_GAME_STUDIO_ROADMAP.md`.

The active product is a Flask-served, vanilla-frontend, three-slot monster
duel with a ten-node PvE campaign, Rebirth-native auth, PostgreSQL persistence, account collection, account
loadout, no-payment booster ownership, progression, guided first-match tutorial, post-match recap,
deck suggestions, beta retention quests, first-session planning, content validation, live telemetry balance
reporting, async replay/ghost contracts, player profile/achievements, match history, economy ledger,
support/admin tooling, feedback capture, self-service export/deletion, consent-gated signup, auth hardening
and release hygiene pages.

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
- `services/rebirth_beta_ops.py`
- `services/rebirth_first_session.py`
- `services/rebirth_retention.py`
- `services/rebirth_content_pipeline.py`
- `services/rebirth_live_balance.py`
- `services/rebirth_async_competition.py`
- `services/rebirth_telemetry.py`
- `services/rebirth_deck_coach.py`
- `services/rebirth_postmatch.py`
- `services/rebirth_schema.py`
- `services/rebirth_campaign.py`
- `templates/index.html`
- `templates/rebirth.html`
- `templates/rebirth_campaign.html`
- `templates/rebirth_product.html`
- `templates/_rebirth_global_nav.html`
- `static/css/rebirth.css`
- `static/css/rebirth_beta.css`
- `static/js/rebirth.js`
- `static/js/rebirth_recap.js`
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
- `POST /api/rebirth/resume`
- `GET /api/rebirth/campaign`
- `POST /api/rebirth/campaign/start`
- `POST /api/rebirth/play-card`
- `POST /api/rebirth/attack`
- `POST /api/rebirth/evolve`
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

State-changing Rebirth APIs require `X-Rebirth-CSRF` by default. Auth endpoints
have a small in-memory rate limit. Password changes are available for signed-in
Rebirth users.

## AAA Studio Foundation Pass

The 2026-06-02 studio-foundation pass moved the next production layer into
Python-owned contracts:

- First 10 minutes are described by `services/rebirth_first_session.py` and
  exposed through `/api/rebirth/first-session` plus `window.REBIRTH_FIRST_SESSION`.
- Retention quests now come from `services/rebirth_retention.py`, including
  daily and weekly beta loops.
- Content/art validation is available through `services/rebirth_content_pipeline.py`
  and `/api/rebirth/content/validate`.
- Real-player balance reporting is available through `services/rebirth_live_balance.py`
  and `/api/rebirth/balance/telemetry`; it deliberately blocks balance claims
  until enough human matches exist.
- Async competition starts with deterministic replay-share and ghost-challenge
  contracts in `services/rebirth_async_competition.py`.
- Guest reconnect now resumes the active in-memory match inside the same session;
  authenticated reconnect remains PostgreSQL-backed.

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
- support feedback linked to account, release version and optional last match
- release dashboard cards for matured-cohort D1/D7 retention, first-match
  completion, tutorial completion, feedback and client errors
- defeated-monster cleanup regression (engine destruction bug)
- mana curve playability (cheapest monster anchored in starter deck)
- campaign unlock/reward/idempotency and boss presentation contracts
- Labs field-fusion persistence and deterministic replay coverage

Current verification for this pass: `python3 -m pytest -q` reported
`1262 passed, 5 skipped, 19 deselected`; focused product/persistence/frontend/balance
tests reported `82 passed`; E2E navigation/auth reported `19 passed`; visual baselines
were captured under `tests/rebirth/visual_baselines/`. Dependency audit must run
against both `requirements.txt` and `requirements-dev.txt` in the supported Python
3.11.9 environment; the local Python 3.9 venv cannot resolve the patched
`requests>=2.33.0` runtime pin.

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
Billing endpoints exist behind a hard closed-beta gate, but checkout and live
payments are disabled by default. There is no active real-money economy runtime.

## Current Limitations

- No real multiplayer.
- No live payment flow; billing is disabled by default and live Stripe keys are blocked unless explicitly allowed after compliance.
- Admin grant support is MVP-only and requires `REBIRTH_ADMIN_TOKEN`.
- Authenticated live in-progress match snapshots are recoverable from persisted
  runtime state; guest in-progress matches remain memory-only.
- One starter collection per account.
- The current asset directory exposes premium bespoke art for selected cards;
  remaining catalog entries use optimized WebP deck art paths.
- Browser screenshots are committed as baseline artifacts under
  `tests/rebirth/visual_baselines/`, but there is not yet a pixel-diff approval workflow.
- The 3961-line `static/js/rebirth.js` is still a single IIFE and would benefit
  from a future modularization pass.
- `static/css/rebirth.css` is still 14270 lines, `services/rebirth_persistence.py`
  is 3157 lines, `app.py` is 2195 lines and `services/rebirth_engine.py` is 2051 lines.
- Durable reconnect is improved for authenticated matches, but guest and active
  in-progress recovery are not yet a complete product.
- External tester launch remains blocked until legal review, Render/Postgres
  backup-restore proof, Sentry/GlitchTip DSN and GitHub closed-beta QA success
  are present.

## Next Steps

- Expand bespoke card art beyond the original 13 silhouettes.
- Modularize `static/js/rebirth.js`, `static/css/rebirth.css`,
  `services/rebirth_persistence.py`, `app.py` and `services/rebirth_engine.py`
  into smaller ownership areas.
- Add pixel-diff or review tooling on top of the committed visual baselines.
- Validate Infernus Core, Shadow Reaper and defensive pacing against real closed-beta
  telemetry before changing card text again.
- Complete the external tester gate before inviting users outside the trusted inner loop.
- Add real payment/economy only if a future product decision asks for it after compliance.
- Keep retired APIs and routes retired unless a future product decision says
  otherwise.
