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
