# Ambitionz Rebirth - AAA Foundation v58

## Scope

This release turns Rebirth into a PostgreSQL-authoritative, mobile-first
foundation while retaining the Arcane Industrial Fantasy visual systems already
present in the arena.

## Phase 1 - Industrial Core

- Production creates repositories only from `REBIRTH_DATABASE_URL` or
  `DATABASE_URL`; SQLite is limited to explicit test execution.
- Flask requests use synchronous SQLAlchemy with `psycopg`, with no per-request
  asyncio loops or async connection pools.
- Database-backed session tokens replace trust in a cookie user id alone.
- Schema migrations cover users, sessions, collections, loadouts, progression,
  rewards, boosters, achievements, wallet, market, audit/telemetry and matches.
- Authenticated matches store both a public snapshot and authoritative runtime
  state, allowing commands to resume after an application restart.
- Wallet and economy ledger records are append-only in product flows. Account
  reset creates compensating movements while retaining the historical trail.
- Gemas/Coinz real-money credit is disabled; the marketplace accepts Ouro only.
- Tutorial and clash reward claims are idempotent against replay.

## Phase 2 - Mobile And Payload Budget

- Phones use a native vertical battlefield instead of shrinking the desktop
  canvas. Action buttons are at least 52 px tall and slot targets at least
  112 px tall.
- Landscape gets a two-column battle/hand arrangement, while tablet/desktop
  retain the cinematic presentation.
- Card art is delivered in WebP. The signature portrait set and 100-card deck
  are constrained by automated size caps.
- The game preloads one fallback art only and lazy-loads visible card images.
- Service worker v58 caches static shell resources only; account HTML, wallet
  pages and API responses remain network-owned.

## Phase 3 - Visual Identity Retained

The living battlefield, parallax, elemental auras, medallion controls, hit
pause, shake, shield fracture, dissolve, evolution and finale overlays remain
active. The performance work does not add expensive CSS filters and preserves
the existing reduced-motion handling.

## Required Verification

```bash
python -m py_compile app.py services/rebirth_persistence.py services/rebirth_schema.py
node --check static/js/rebirth.js
node --check static/js/rebirth_product.js
node --check static/js/service-worker.js
pytest tests/rebirth -q
pytest tests/rebirth -m e2e -q
pytest tests/rebirth -m requires_postgres -q
```

The PostgreSQL-marked suite requires Docker/Testcontainers in CI. It validates
schema migration, process-restart persistence and serialized market contention.
