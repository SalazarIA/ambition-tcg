# Rebirth Release Status

## Official Product State

Ambitionz Rebirth is the only active Ambitionz runtime product.

The active product is a Flask-served, vanilla frontend, single-screen monster
duel MVP. The old Arena, Ascension, BE2, SocketIO, economy, progression, shop,
collection and deck builder systems are retired from runtime and must not be
restored just to satisfy historical tests.

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
- `templates/index.html`
- `templates/rebirth.html`
- `static/css/rebirth.css`
- `static/js/rebirth.js`
- `static/js/pwa.js`
- `static/js/service-worker.js`
- `static/manifest.webmanifest`
- `static/assets/rebirth/manifest.json`
- `static/assets/rebirth/cards/*-art.png`
- `static/assets/rebirth/ui/*`

## Active Browser Routes

- `GET /`
- `GET /rebirth`
- `GET /health`
- `GET /manifest.webmanifest`
- `GET /service-worker.js`

Retired browser routes redirect to `/rebirth`; examples include `/arena`,
`/training`, `/training-legacy`, `/collection`, `/deck-builder`, `/shop`,
`/ranking`, `/leaderboard`, `/missions`, `/progression`, `/campaign`,
`/tutorial`, `/how-to-play`, `/inventory`, `/economy` and `/match-history`.

## Active APIs

- `POST /api/rebirth/start`
- `POST /api/rebirth/play-card`
- `POST /api/rebirth/evolve`
- `POST /api/rebirth/next-turn`

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

Current local result for this block:

```text
36 passed
```

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

No database has been added in this block.

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

The active service worker cache is `ambitionz-rebirth-release-hygiene-v6` and
does not cache Arena or Ascension assets.

## Current Limitations

- No real multiplayer.
- No account progression.
- No database persistence for match history.
- In-memory matches are lost on process restart or deploy.
- Rebirth has one starter deck and deterministic bot behavior.
- Browser visual QA is still recommended before public release.
- Historical docs and archived tests may describe retired systems; current
  Rebirth docs are authoritative.

## Next Steps

- Add Rebirth-native persistence only after the active state contract stabilizes.
- Add Rebirth balance simulations and tuning.
- Add screenshot-based visual QA for desktop/mobile `/rebirth`.
- Migrate only useful old-product ideas into Rebirth-native contracts.
- Keep retired APIs and routes retired unless a future product decision says
  otherwise.
