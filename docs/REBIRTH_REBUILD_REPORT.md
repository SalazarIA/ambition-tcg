# Ambitionz Rebirth Rebuild Report

## Product Reset

The active product was rebuilt around `Ambitionz Rebirth`, a simple one-card monster duel:

- One card chosen by the player each turn.
- One bot response each turn.
- Higher power wins.
- Losing side loses 1 HP.
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
- Home mobile screenshot: `/Users/lucassilverio/Desktop/Ambition/.codex-artifacts/rebirth-home-mobile.png`
- Game mobile screenshot: `/Users/lucassilverio/Desktop/Ambition/.codex-artifacts/rebirth-mobile.png`
- Game desktop screenshot: `/Users/lucassilverio/Desktop/Ambition/.codex-artifacts/rebirth-desktop.png`
- Post-clash mobile screenshot: `/Users/lucassilverio/Desktop/Ambition/.codex-artifacts/rebirth-mobile-after-clash-fixed.png`
