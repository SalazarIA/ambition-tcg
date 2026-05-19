# Ambitionz Rebirth

Ambitionz Rebirth is the active Ambitionz MVP: a fast, single-screen monster
duel where the player chooses one card, the bot answers with one card, and the
clash resolves through the Rebirth rules engine.

The previous Arena, Ascension, BE2, economy, progression, shop, collection and
deck-builder product surfaces are retired from the active runtime. They remain
in the repository only as historical context while Rebirth becomes the official
product path.

## Active Stack

- Python
- Flask
- Vanilla HTML/CSS/JavaScript
- PWA manifest and service worker
- In-memory Rebirth match store with TTL and max-entry cleanup
- Gunicorn for deployment

The current runtime does not initialize SocketIO, SQLAlchemy, a database,
legacy economy systems or the old multiplayer arena.

## Active Routes

- `GET /` - Rebirth home
- `GET /rebirth` - playable Rebirth MVP
- `GET /health` - deploy health JSON
- `GET /manifest.webmanifest`
- `GET /service-worker.js`

## Active APIs

- `POST /api/rebirth/start`
- `POST /api/rebirth/play-card`
- `POST /api/rebirth/evolve`
- `POST /api/rebirth/next-turn`

Retired browser routes such as `/arena`, `/training`, `/collection`,
`/deck-builder`, `/shop`, `/missions`, `/progression`, `/campaign`,
`/tutorial`, `/inventory`, `/economy` and `/match-history` redirect to
`/rebirth`.

Retired API groups such as `/api/ascension/*`, `/api/beta/*` and
`/api/booster/*` return `410 legacy_disabled`.

## Run Locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open:

```text
http://127.0.0.1:8080/
http://127.0.0.1:8080/rebirth
```

## Test

```bash
pip install -r requirements-dev.txt
python3 -m py_compile app.py services/rebirth_engine.py services/rebirth_cards.py services/rebirth_bot.py services/rebirth_state.py services/rebirth_match_store.py
python3 -m pytest -q
node --check static/js/rebirth.js
node --check static/js/service-worker.js
node --check static/js/pwa.js
```

The standard pytest suite is scoped to `tests/rebirth` through `pytest.ini`.
Tests for the retired pre-Rebirth product are preserved under
`tests/legacy_disabled` and are not authoritative for the active product.

## Development Tools

Runtime dependencies stay intentionally small in `requirements.txt`. Development
and local tooling dependencies live in `requirements-dev.txt`; this includes
pytest, Pillow for the local card-art pipeline and Playwright for optional QA
scripts.

## Historical Docs

Some older documentation still describes Arena, Ascension, BE2, economy,
progression or SocketIO-era work. Treat those files as historical unless a
current Rebirth status document says otherwise. The current source of truth is:

- `docs/REBIRTH_RELEASE_STATUS.md`
- `docs/REBIRTH_ARCHITECTURE.md`
- `docs/LEGACY_REMOVAL_REPORT.md`
- `docs/REBIRTH_REBUILD_REPORT.md`
