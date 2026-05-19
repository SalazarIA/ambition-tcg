# Legacy Cleanup Map

## Rebirth Canonical Surface

- `/`
- `/rebirth`
- `/health`
- `/api/rebirth/start`
- `/api/rebirth/play-card`
- `/api/rebirth/evolve`
- `/api/rebirth/next-turn`
- `services/rebirth_contracts.py`
- `services/rebirth_cards.py`
- `services/rebirth_art.py`
- `services/rebirth_bot.py`
- `services/rebirth_state.py`
- `services/rebirth_serializers.py`
- `services/rebirth_match_store.py`
- `services/rebirth_engine.py`
- `templates/index.html`
- `templates/rebirth.html`
- `static/css/rebirth.css`
- `static/js/rebirth.js`
- `static/js/pwa.js`
- `static/js/service-worker.js`
- `static/assets/rebirth/*`
- `tests/rebirth/*`

## Retired Browser Surface

These routes are retired in runtime and redirect to `/rebirth`:

- `/training`
- `/training-legacy`
- `/arena`
- `/collection`
- `/deck-builder`
- `/shop`
- `/ranking`
- `/leaderboard`
- `/missions`
- `/progression`
- `/campaign`
- `/tutorial`
- `/how-to-play`
- `/inventory`
- `/economy`
- `/match-history`

## Retired API Surface

These API groups are retired in runtime and return `410 legacy_disabled`:

- `/api/ascension/*`
- `/api/beta/*`
- `/api/booster/*`

## Historical Code

Files for Arena, Ascension, BE2, SocketIO, SQLAlchemy/database-backed systems,
economy, shop, collection, progression and old deck builder remain in the
repository for reference. They are not active release targets.

Historical tests are stored under `tests/legacy_disabled`.

## Cleanup Rule

- Do not re-enable retired systems to satisfy old tests.
- Do not import legacy Arena/Ascension CSS or JavaScript into `/` or `/rebirth`.
- Do not add SocketIO, SQLAlchemy, economy or account persistence back into the
  active runtime without a new explicit product decision.
- Migrate useful retired ideas into Rebirth-native APIs, tests and docs.
- Keep reports and large local QA artifacts untouched unless a dedicated cleanup
  task asks for them.
