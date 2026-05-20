# Ambitionz Rebirth Rebuild Report

## Product Reset

The active product was rebuilt around `Ambitionz Rebirth`, a simple one-card monster duel:

- One card chosen by the player each turn.
- One bot response each turn.
- Higher attack wins.
- Winning card deals attack-versus-guard damage.
- Ties are Clash turns with no damage.
- Duplicate base monsters can evolve into stronger monsters.

## Active Architecture

- `app.py` is now a minimal Flask production app.
- `services/rebirth_cards.py` owns the deterministic monster catalog and decks.
- `services/rebirth_state.py` owns match state, hands, drawing and public JSON shape.
- `services/rebirth_bot.py` owns the deterministic bot response rule.
- `services/rebirth_engine.py` owns play, compare, damage, evolution, next-turn and finish logic.
- `templates/index.html` is the new Rebirth home.
- `templates/rebirth.html` is the new playable prototype.
- `static/css/rebirth.css` is the only active product stylesheet.
- `static/js/rebirth.js` is the only active gameplay script.

## Deploy Surface

Preserved:

- Project name and repository.
- `render.yaml`.
- `requirements.txt`.
- `Procfile` and lowercase `procfile`.
- `GET /health`.
- Gunicorn start command targeting `app:app`.

Changed:

- Render predeploy database migration was removed because the active MVP no longer initializes SQLAlchemy or Flask-Migrate.
- Legacy environment variables for beta auth, email, retention and Socket.io were removed from `render.yaml`.
- The existing database resource is still listed in `render.yaml` to avoid destructive infrastructure churn.

## Local Run

```bash
python3 app.py
```

Then open:

```text
http://127.0.0.1:8080
http://127.0.0.1:8080/rebirth
```

## Test Commands

```bash
python3 -m py_compile app.py services/rebirth_engine.py services/rebirth_cards.py services/rebirth_bot.py services/rebirth_state.py
python3 -m pytest -q
node --check static/js/rebirth.js
```

## Validation Result

- `python3 -m py_compile app.py services/rebirth_engine.py services/rebirth_cards.py services/rebirth_bot.py services/rebirth_state.py`: passed
- `python3 -m pytest -q`: 16 passed
- `node --check static/js/rebirth.js`: passed
- Local Playwright smoke: `/`, `/rebirth`, `POST /api/rebirth/start`, `POST /api/rebirth/evolve`, `POST /api/rebirth/play-card`

## Visual QA Artifacts

- Concept image: `/Users/lucassilverio/.codex/generated_images/019e3dd4-0a27-76b1-adec-2fdb984b4a03/ig_054d19fb90dd7387016a0bbb80782081919fc1331c8de15e9f.png`
- Temporary home, game and post-clash screenshots were captured during local QA and removed before handoff.

## Rebirth 001 - Lock Visual Standard + Product Polish

The approved visual pattern is now documented as `Ambitionz Rebirth Premium Clash UI` in `docs/REBIRTH_VISUAL_STANDARD.md`.

Files changed in this block:

- `docs/REBIRTH_VISUAL_STANDARD.md`
- `templates/rebirth.html`
- `static/css/rebirth.css`
- `static/js/rebirth.js`
- `tests/test_rebirth_routes.py`
- `docs/REBIRTH_REBUILD_REPORT.md`

What changed:

- Locked the mobile-first hierarchy around top HUD, slogan strip, bot card zone, main card, duplicate/evolution panel, hand, actions, result and compact log.
- Preserved the approved dark premium direction with gold player/action language and cyan bot language.
- Renamed the visible duplicate action to COMBINE while keeping the existing `/api/rebirth/evolve` API and `evolve-button` ID.
- Added stronger card frames, angular panel cuts, clearer selected-card feedback and visual result states for Victory, Defeat and Clash.
- Added route tests for Rebirth CSS/JS references, required slogan text and all JS-owned IDs.

QA executed for Rebirth 001:

- `python3 -m py_compile app.py services/rebirth_engine.py services/rebirth_cards.py services/rebirth_bot.py services/rebirth_state.py`
- `python3 -m pytest -q`
- `node --check static/js/rebirth.js`
- Local Playwright visual smoke on 390x844 and 1280x900 viewports.

Rebirth 001 validation result:

- `py_compile`: passed
- `pytest -q`: 17 passed
- `node --check`: passed
- Visual smoke: no horizontal overflow, HUD present, six slogan lines present, 5 hand cards present, COMBINE visible on duplicate, Victory state class applied after clash.

Rebirth 001 visual artifacts:

- Temporary mobile, desktop and post-clash screenshots were captured during local QA and removed before handoff.

Next recommended block:

- Rebirth 002: card art identity pass, monster family silhouettes and small animation/haptics pass for select, combine, clash and next turn.

## Rebirth 002 - Reference Match Architecture Rebuild

The Rebirth product was rebuilt to match the provided premium card battler reference more closely across backend, engine, assets and UI.

Files changed in this block:

- `services/rebirth_cards.py`
- `services/rebirth_state.py`
- `services/rebirth_bot.py`
- `services/rebirth_engine.py`
- `templates/rebirth.html`
- `static/css/rebirth.css`
- `static/js/rebirth.js`
- `static/js/service-worker.js`
- `static/assets/rebirth/cards/*.svg`
- `tests/test_rebirth_engine.py`
- `tests/test_rebirth_routes.py`
- `tests/test_rebirth_frontend_contract.py`
- `pytest.ini`
- `docs/REBIRTH_RULEBOOK.md`
- `docs/REBIRTH_VISUAL_STANDARD.md`
- `docs/REBIRTH_REBUILD_REPORT.md`

What changed:

- Rebuilt the data model around reference-style monsters: Dreadclaw, Stoneshell, Shadewisp, Skywarden, Ironbastion, Embermaw, Voidstalker and Nightfang.
- Replaced 3-life damage with a 30 HP clash model.
- Added attack, guard, role, ability name, ability text and static card art paths to every card.
- Reworked bot response logic to answer with a stronger attack when possible, otherwise with the best guard.
- Rebuilt damage resolution around winner attack versus loser guard, with minimum 1 damage and Clash ties causing no damage.
- Rebuilt the `/rebirth` DOM into the reference hierarchy: top HUD, bot card, slogans, large main monster card, duplicate rail, mini hand, CLASH/COMBINE actions, turn log, CTA and New Match.
- Added custom SVG monster art assets under `static/assets/rebirth/cards/`.
- Updated the service worker to cache the active Rebirth clash assets.
- Expanded tests to cover the frontend contract and new engine model.

QA executed for Rebirth 002:

- `python3 -m py_compile app.py services/rebirth_engine.py services/rebirth_cards.py services/rebirth_bot.py services/rebirth_state.py`
- `python3 -m pytest -q`
- `node --check static/js/rebirth.js`
- Local Playwright visual smoke on 390x844, 860x1880 and 1280x900 viewports.

Rebirth 002 validation result:

- `py_compile`: passed
- `pytest -q`: 20 passed
- `node --check`: passed
- Visual smoke: no horizontal overflow, selected Dreadclaw renders as the main card, duplicate COMBINE is enabled, HP bars render, 5 mini cards render, CTA renders, reference viewport keeps side evolution rail.

Next recommended block:

- Rebirth 003: improve card art fidelity with higher-detail raster or SVG assets, add clash animations and tune the first five-turn balance curve.

## Rebirth 003 - Visual Fidelity Correction

This correction locks the live `/rebirth` screen to the approved reference composition instead of a loose interpretation.

Files changed in this correction:

- `services/rebirth_cards.py`
- `static/css/rebirth.css`
- `static/js/rebirth.js`
- `static/js/service-worker.js`
- `static/assets/rebirth/cards/dreadclaw-art.png`
- `static/assets/rebirth/ui/bot-card-back.png`
- `static/assets/rebirth/ui/bot-emblem.png`
- `tests/test_rebirth_frontend_contract.py`
- `docs/REBIRTH_VISUAL_STANDARD.md`
- `docs/REBIRTH_REBUILD_REPORT.md`

What changed:

- Re-centered the main monster card on the 860px reference board and moved the duplicate panel into a right-side rail.
- Reduced the live layout drift that made desktop open on a stretched, cropped card view.
- Forced `/rebirth` to restore scroll to the top so the HUD is visible on reload.
- Replaced the placeholder Dreadclaw SVG in the active product with a raster crop from the approved concept art.
- Replaced CSS-generated bot placeholder shapes with approved bot emblem and bot-card-back assets.
- Updated the service worker cache to the active raster/reference assets and removed the old Dreadclaw SVG from the active cache list.
- Added frontend contract coverage for the reference asset lock.

QA executed for this correction:

- `python3 -m py_compile app.py services/rebirth_engine.py services/rebirth_cards.py services/rebirth_bot.py services/rebirth_state.py`
- `python3 -m pytest -q`
- `node --check static/js/rebirth.js`
- Local Playwright visual QA on 860x1880, 1440x900 and 390x844 viewports.
- Verified no horizontal overflow, scroll starts at top, 5 hand cards render, COMBINE is enabled, and Dreadclaw uses `/static/assets/rebirth/cards/dreadclaw-art.png`.

Validation result:

- `py_compile`: passed
- `pytest -q`: 21 passed
- `node --check`: passed
- Visual QA: passed on 860x1880, 1440x900 and 390x844 with no horizontal overflow.

Next recommended block:

- Rebirth 004: replace the remaining secondary SVG monster placeholders with premium raster art so the whole hand matches the approved Dreadclaw quality.

## Rebirth 004 - Product Architecture Lock + Single Screen Game System

Rebirth 004 moves the product from a tall page interpretation into a locked single-screen web-game architecture.

Files created in this block:

- `services/rebirth_contracts.py`
- `services/rebirth_match_store.py`
- `services/rebirth_serializers.py`
- `static/assets/rebirth/manifest.json`

Files changed in this block:

- `app.py`
- `services/rebirth_engine.py`
- `services/rebirth_state.py`
- `templates/index.html`
- `templates/rebirth.html`
- `static/css/rebirth.css`
- `static/js/rebirth.js`
- `static/js/service-worker.js`
- `pytest.ini`
- `tests/test_rebirth_engine.py`
- `tests/test_rebirth_routes.py`
- `tests/test_rebirth_frontend_contract.py`
- `tests/test_rebirth_home_promotion.py`
- `docs/REBIRTH_ARCHITECTURE.md`
- `docs/REBIRTH_RULEBOOK.md`
- `docs/REBIRTH_VISUAL_STANDARD.md`
- `docs/REBIRTH_REBUILD_REPORT.md`

What changed:

- Split backend responsibilities into contracts, match store, serializers, state, engine, bot and cards.
- Locked phases to `choose`, `result` and `finished`.
- Replaced old expected-error codes with stable API codes: `missing_match`, `invalid_phase`, `missing_card`, `invalid_card`, `duplicate_not_available`, `match_finished` and `malformed_request`.
- Updated Flask API responses to always include `ok`, `state` and `result` on success.
- Ensured expected player/request mistakes return JSON with 400/404/409 instead of 500.
- Rebuilt `/rebirth` as a fixed `852px x 1846px` game board scaled into the viewport.
- Added `rb-game-viewport`, `rb-game-board`, `rb-main-card`, `rb-duplicate-panel`, `rb-asset-fallback` and related locked component classes.
- Rewrote `static/js/rebirth.js` into internal modules: `RebirthApi`, `RebirthStore`, `RebirthRenderer`, `RebirthInput`, `RebirthBoardScaler`, `RebirthAssets` and `RebirthErrors`.
- Added anti-scroll behavior so wheel and document scroll do not move `/rebirth`.
- Rebuilt the home as a Rebirth-only premium page with no old Arena/Ascension CTAs.
- Added an explicit active Rebirth asset manifest and updated the service worker cache to `ambitionz-rebirth-single-screen-v4`.
- Expanded tests to include API error contracts, frontend active asset contracts, home Rebirth positioning and single-screen runtime markers.

QA executed for Rebirth 004:

- `python3 -m py_compile app.py services/rebirth_engine.py services/rebirth_cards.py services/rebirth_bot.py services/rebirth_state.py services/rebirth_contracts.py services/rebirth_match_store.py services/rebirth_serializers.py`
- `python3 -m pytest -q`
- `node --check static/js/rebirth.js`
- Local Playwright rendered QA on 390x844, 852x1846, 1440x900 and 2048x1218 viewports.

Rebirth 004 validation result:

- `py_compile`: passed
- `pytest -q`: 27 passed
- `node --check`: passed
- Visual QA: passed on all required viewports.
- No document scroll on `/rebirth`.
- Wheel did not change `scrollY`.
- No horizontal overflow.
- No console errors.
- No page errors.
- No asset 404s.
- No native broken-image icons.
- Core flow passed: start -> combine -> clash -> next turn.

Remaining constraint:

- Secondary monster art is still SVG placeholder-level and intentionally deferred to the next premium art block.

Next recommended block:

- Rebirth 005: Premium Monster Identity + Card Art System.

## Rebirth 004 - Repository Truth + Release Hygiene

This block makes the repository match the official product decision:
Ambitionz Rebirth is the only active runtime product.

Decision applied:

- Arena, Ascension, BE2, SocketIO, SQLAlchemy/database-backed account systems,
  economy, progression, shop, collection and old deck builder remain retired.
- Retired browser routes redirect to `/rebirth`.
- Retired API groups return `410 legacy_disabled`.
- No legacy API, database, SocketIO or economy system was restored for test
  compatibility.

Files created in this block:

- `tests/legacy_disabled/README.md`
- `tests/legacy_disabled/conftest.py`
- `tests/rebirth/test_rebirth_deploy_smoke.py`
- `tests/rebirth/test_rebirth_match_store.py`
- `tests/rebirth/test_rebirth_security_headers.py`

Files changed in this block:

- `README.md`
- `app.py`
- `pytest.ini`
- `requirements-dev.txt`
- `services/rebirth_match_store.py`
- `static/js/service-worker.js`
- `tests/rebirth/test_rebirth_frontend_contract.py`
- `docs/REBIRTH_RELEASE_STATUS.md`
- `docs/LEGACY_REMOVAL_REPORT.md`
- `docs/LEGACY_CLEANUP_MAP.md`
- `docs/REBIRTH_ARCHITECTURE.md`
- `docs/REBIRTH_REBUILD_REPORT.md`

Files moved or archived:

- Active Rebirth tests moved to `tests/rebirth`.
- Pre-Rebirth historical tests moved to `tests/legacy_disabled`.
- `tests/legacy_disabled` is intentionally outside the default release suite
  because those tests target retired product surfaces.

What changed:

- Replaced the old `pytest.ini` file-name allowlist with explicit
  `testpaths = tests/rebirth`.
- Added an honest deploy smoke covering `/`, `/rebirth`, `/health`,
  `/api/rebirth/start`, `/api/rebirth/evolve`, `/api/rebirth/play-card`,
  retired browser redirects and retired API `410 legacy_disabled`.
- Added security headers through `app.after_request`.
- Added service worker root-scope header for `/service-worker.js`.
- Added TTL expiry, defensive cleanup, max-entry trimming and basic locking to
  the in-memory match store.
- Bumped active service worker cache to
  `ambitionz-rebirth-release-hygiene-v6`.
- Updated current docs so old Arena/Ascension/economy claims are historical,
  not release truth.
- Updated development requirements to include pytest, Pillow and Playwright
  without adding them to runtime requirements.

Security headers:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`
- CSP limited to local sources with `unsafe-inline` kept for current inline
  bootstrap data and inline card styles.

Match store:

- Default TTL: `3600` seconds.
- Default max matches: `512`.
- Environment overrides: `REBIRTH_MATCH_TTL_SECONDS`,
  `REBIRTH_MAX_MATCHES`.
- Still no database persistence.

QA executed for this block:

- `python3 -m py_compile app.py services/rebirth_engine.py services/rebirth_cards.py services/rebirth_bot.py services/rebirth_state.py services/rebirth_match_store.py`
- `python3 -m pytest -q`
- `node --check static/js/rebirth.js`
- `node --check static/js/service-worker.js`
- `node --check static/js/pwa.js`
- `git status --short`
- `git diff --stat`

Validation result:

- `py_compile`: passed
- `pytest -q`: 36 passed
- `node --check static/js/rebirth.js`: passed
- `node --check static/js/service-worker.js`: passed
- `node --check static/js/pwa.js`: passed

Next recommended block at the time:

- Superseded by Rebirth 005-010 below.

## Rebirth 005-010 - Restore Product Shell Through Desktop Arena Polish

This block restores the active Rebirth product shell without reactivating the
retired Arena/Ascension/economy runtime.

Decision applied:

- Ambitionz Rebirth remains the only active runtime product.
- New collection, shop, progression and account surfaces live under
  `/rebirth/...`; retired top-level legacy routes still redirect to `/rebirth`.
- Booster, loadout and progression behavior are explicit demo/preview contracts.
- No database, SocketIO, SQLAlchemy, payment flow or legacy economy was added.

Blocks completed:

- Rebirth 005 - restored the product shell on `/` and added Rebirth section
  navigation.
- Rebirth 006 - added `/rebirth/account`, `/api/rebirth/auth-plan` and
  `docs/REBIRTH_AUTH_PLAN.md` as the real auth plan without fake login.
- Rebirth 007 - added Rebirth-native collection/loadout preview and loadout
  validation.
- Rebirth 008 - added no-payment shop and booster demo under
  `/rebirth/shop` and `/api/rebirth/booster/open`.
- Rebirth 009 - added progression/rewards preview without old economy
  mutation.
- Rebirth 010 - added desktop arena rails around the fixed portrait board
  without changing game rules.

Files created in this block:

- `services/rebirth_product.py`
- `templates/rebirth_product.html`
- `static/js/rebirth_product.js`
- `tests/rebirth/test_rebirth_product_shell.py`
- `docs/REBIRTH_AUTH_PLAN.md`

Files changed in this block:

- `app.py`
- `README.md`
- `templates/index.html`
- `templates/rebirth.html`
- `static/css/rebirth.css`
- `static/js/service-worker.js`
- `tests/rebirth/test_rebirth_deploy_smoke.py`
- `tests/rebirth/test_rebirth_frontend_contract.py`
- `docs/REBIRTH_RELEASE_STATUS.md`
- `docs/REBIRTH_ARCHITECTURE.md`
- `docs/LEGACY_REMOVAL_REPORT.md`
- `docs/REBIRTH_REBUILD_REPORT.md`

Files moved or archived:

- None in this block. Legacy tests remain archived under
  `tests/legacy_disabled` from Rebirth 004.

QA executed for this block:

- `python3 -m py_compile app.py services/rebirth_engine.py services/rebirth_cards.py services/rebirth_bot.py services/rebirth_state.py services/rebirth_match_store.py services/rebirth_product.py`
- `python3 -m pytest -q`
- `node --check static/js/rebirth.js`
- `node --check static/js/service-worker.js`
- `node --check static/js/pwa.js`
- `node --check static/js/rebirth_product.js`
- Browser smoke on `/rebirth/account`, `/rebirth/profile`, `/rebirth/shop`,
  `/rebirth`, `/rebirth/onboarding`, `/rebirth/progression`,
  `/rebirth/balance` and `/rebirth/release`.
- Browser mobile smoke on `/rebirth/profile` and `/rebirth` at `390x844`.
- Browser render smoke on `/`, `/rebirth`, `/rebirth/account`,
  `/rebirth/collection`, `/rebirth/shop`, `/rebirth/progression` and
  `/rebirth/desktop`.
- Browser interaction smoke for booster opening and loadout validation.

Validation result:

- `py_compile`: passed
- `pytest -q`: 41 passed
- `node --check static/js/rebirth.js`: passed
- `node --check static/js/service-worker.js`: passed
- `node --check static/js/pwa.js`: passed
- Browser smoke: passed; account registration, CSRF-backed booster opening,
  clash resolution, tutorial completion, daily reward claim, profile
  achievements, balance rerun and release page rendered without console errors.
- `node --check static/js/rebirth_product.js`: passed
- Browser smoke: passed; no console errors observed in the checked flows.

Next recommended block:

- Rebirth 011: Real persistence/auth implementation plan execution, starting
  with a deliberate storage choice and Rebirth-native user/session schema.

## Rebirth 011-019 - Persisted MVP Release Candidate

This block turns the Rebirth product shell into a persisted MVP release
candidate while keeping all retired systems retired.

Decision applied:

- Rebirth persistence uses Python stdlib SQLite at `instance/rebirth.db` by
  default.
- No SQLAlchemy, SocketIO, old economy, old collection, old shop, old
  progression or legacy account runtime was restored.
- Anonymous users can browse product pages, but ownership mutations require a
  signed-in Rebirth account.

Blocks completed:

- Real Auth/Persistence: account register/login/logout/session with PBKDF2
  password hashes.
- User Collection Persistida: starter collection and booster cards persist per
  Rebirth user.
- Deck/Loadout Real por Conta: loadout validation persists and `/api/rebirth/start`
  uses the signed-in account loadout.
- Progression + Rewards Persistidos: clashes, wins/losses, XP, boosters, daily
  reward and tutorial completion persist.
- Shop + Booster Ownership: no-payment booster opening mutates signed-in
  collection and booster history.
- Onboarding/Tutorial Rebirth: `/rebirth/onboarding` and completion endpoint.
- Balance + Bot Tuning + Simulations: deterministic simulation endpoint and
  `/rebirth/balance` page.
- QA Visual/PWA/Offline/Responsivo: service worker cache bumped to
  `ambitionz-rebirth-release-candidate-v19` with only active Rebirth routes and
  assets.
- Release Candidate + Deploy Hygiene Final: `/rebirth/release` and
  `docs/REBIRTH_RELEASE_CANDIDATE.md`.

Files created in this block:

- `services/rebirth_persistence.py`
- `services/rebirth_balance.py`
- `tests/rebirth/test_rebirth_persistence.py`
- `docs/REBIRTH_RELEASE_CANDIDATE.md`

Files changed in this block:

- `app.py`
- `README.md`
- `services/rebirth_cards.py`
- `services/rebirth_state.py`
- `services/rebirth_engine.py`
- `services/rebirth_product.py`
- `templates/index.html`
- `templates/rebirth.html`
- `templates/rebirth_product.html`
- `static/css/rebirth.css`
- `static/js/rebirth_product.js`
- `static/js/service-worker.js`
- `tests/conftest.py`
- `tests/rebirth/test_rebirth_deploy_smoke.py`
- `tests/rebirth/test_rebirth_frontend_contract.py`
- `tests/rebirth/test_rebirth_product_shell.py`
- `docs/REBIRTH_RELEASE_STATUS.md`
- `docs/REBIRTH_ARCHITECTURE.md`
- `docs/LEGACY_REMOVAL_REPORT.md`
- `docs/REBIRTH_UI_CONTRACT.md`
- `docs/REBIRTH_AUTH_PLAN.md`
- `docs/REBIRTH_REBUILD_REPORT.md`

Files moved or archived:

- None. Legacy tests remain archived under `tests/legacy_disabled`.

QA executed for this block:

- `python3 -m py_compile app.py services/rebirth_engine.py services/rebirth_cards.py services/rebirth_bot.py services/rebirth_state.py services/rebirth_match_store.py services/rebirth_product.py services/rebirth_persistence.py services/rebirth_balance.py`
- `python3 -m pytest -q`
- `node --check static/js/rebirth.js`
- `node --check static/js/rebirth_product.js`
- `node --check static/js/service-worker.js`
- `node --check static/js/pwa.js`
- Browser smoke on `/`, `/rebirth/account`, `/rebirth/shop`,
  `/rebirth/collection`, `/rebirth/onboarding`, `/rebirth/balance`,
  `/rebirth/release` and `/rebirth`.
- Browser mobile smoke on `/rebirth/collection` at `390x844`.

Validation result at this point:

- `py_compile`: passed
- `pytest -q`: 47 passed
- `node --check static/js/rebirth.js`: passed
- `node --check static/js/rebirth_product.js`: passed
- `node --check static/js/service-worker.js`: passed
- `node --check static/js/pwa.js`: passed
- Browser smoke: passed; account registration, booster ownership, loadout save,
  tutorial completion and balance rerun all rendered without console errors.

Next recommended block:

- Rebirth 020: production auth hardening, including CSRF/rate limiting/session
  rotation and admin support tooling.

## Rebirth 020 - Final MVP Hardening + Profile

This block closes the remaining MVP gaps without reactivating any retired
Arena, Ascension, SocketIO, SQLAlchemy or economy runtime.

Decision applied:

- Ambitionz Rebirth remains the only active product.
- Rebirth accounts, collection, loadout, progression, rewards, achievements and
  profile state are persisted in the Rebirth SQLite store.
- State-changing Rebirth JSON APIs use a session CSRF token by default.
- Auth endpoints have a small process-local throttle.
- Password changes are supported for signed-in Rebirth accounts.

Blocks completed:

- Auth hardening: CSRF endpoint, template token injection, JS header wiring,
  session rotation on register/login and logout session clearing.
- Rate limiting: register/login/change-password throttling with stable
  `rate_limited` JSON errors.
- Profile + Achievements: `/rebirth/profile`, `/api/rebirth/profile`,
  persisted achievement unlocks and profile stats.
- Account controls: signed-in password change flow in the Rebirth product shell.
- PWA final cache: service worker cache bumped to
  `ambitionz-rebirth-final-mvp-v20` and includes `/rebirth/profile`.
- Release truth: README/status/architecture/auth/UI/release docs updated with
  the current active routes, APIs and test count.

Files created in this block:

- `tests/rebirth/test_rebirth_auth_security.py`

Files changed in this block:

- `app.py`
- `README.md`
- `services/rebirth_persistence.py`
- `services/rebirth_product.py`
- `templates/index.html`
- `templates/rebirth.html`
- `templates/rebirth_product.html`
- `static/css/rebirth.css`
- `static/js/rebirth.js`
- `static/js/rebirth_product.js`
- `static/js/service-worker.js`
- `tests/conftest.py`
- `tests/rebirth/test_rebirth_frontend_contract.py`
- `tests/rebirth/test_rebirth_persistence.py`
- `tests/rebirth/test_rebirth_product_shell.py`
- `docs/REBIRTH_RELEASE_STATUS.md`
- `docs/REBIRTH_ARCHITECTURE.md`
- `docs/REBIRTH_UI_CONTRACT.md`
- `docs/REBIRTH_AUTH_PLAN.md`
- `docs/REBIRTH_RELEASE_CANDIDATE.md`
- `docs/LEGACY_REMOVAL_REPORT.md`
- `docs/REBIRTH_REBUILD_REPORT.md`

Files moved or archived:

- None. Legacy tests remain archived under `tests/legacy_disabled`.

QA executed for this block:

- `python3 -m py_compile app.py services/rebirth_engine.py services/rebirth_cards.py services/rebirth_bot.py services/rebirth_state.py services/rebirth_match_store.py services/rebirth_product.py services/rebirth_persistence.py services/rebirth_balance.py`
- `python3 -m pytest -q`
- `node --check static/js/rebirth.js`
- `node --check static/js/rebirth_product.js`
- `node --check static/js/service-worker.js`
- `node --check static/js/pwa.js`

Validation result at this point:

- `py_compile`: passed
- `pytest -q`: 51 passed
- `node --check static/js/rebirth.js`: passed
- `node --check static/js/rebirth_product.js`: passed
- `node --check static/js/service-worker.js`: passed
- `node --check static/js/pwa.js`: passed

Next recommended block:

- No new gameplay block is required for the current MVP. The next logical work
  is production operations: deploy target config, admin support tooling,
  backup/restore policy for `REBIRTH_DB_PATH`, screenshot baselines and a real
  payment/multiplayer decision only if product scope expands.
