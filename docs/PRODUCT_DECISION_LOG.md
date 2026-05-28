# Product Decision Log

## 2026-05-20 - Ambitionz Rebirth Is The Only Active Product

Decision:

- Ambitionz Rebirth is the active Ambitionz runtime and product surface.
- The current game identity is: **three-slot tactical TCG with chained
  resolution, fusion lab and ten-encounter campaign**.
- The current genre framing is: **tactical card battler**: two sides, three
  active battlefield slots each, hand of cards with mana cost, evolution +
  fusion as secondary actions, deterministic combat resolution per turn.
- Arena, Ascension, BE2, legacy economy, legacy progression, old shop, old
  collection and old deck builder are retired from runtime.

> Historical note (kept for context): the original framing was "One card. One
> decision. One clash." That framing predates the v59 three-slot rework,
> v69 fusion lab and v71/v72 campaign. Anything still describing Rebirth as a
> one-card duel is out of date and should be reconciled against
> [REBIRTH_RULEBOOK.md](REBIRTH_RULEBOOK.md).

Why:

- The repository had multiple historical product directions competing for
  truth.
- Rebirth now has the clearest playable loop, card identity and product shell.
- The technical path from the TCG report is to harden foundation before adding
  multiplayer or monetization.

Guardrails:

- Do not restore retired APIs to satisfy historical tests.
- Do not reintroduce SocketIO, SQLAlchemy or the old economy as runtime defaults.
- Future systems must be Rebirth-native and server-authoritative.
- Docs that describe old Arena/Ascension systems are historical unless a
  current Rebirth status document explicitly promotes them.

## 2026-05-20 - Season 0 Architecture Hardening

Decision:

- Implement the PDF's foundation recommendations before expanding gameplay.
- Add command/event/state hash contracts to active matches.
- Persist signed-in match history, commands, events and economy ledger entries.
- Add self-service export/reset and token-protected admin grant APIs.
- Make Balance Lab use the active engine with player duplicate evolution.
- Keep real-money payments and real-time multiplayer out of this block.

Why:

- A professional TCG needs auditability, replay source data, economy movement
  history, support tooling and deterministic simulation.
- Rebirth is still an MVP, but these contracts prevent the next feature layer
  from becoming untraceable.

## 2026-05-23 - AAA Foundation PostgreSQL Cutover

Decision:

- Production Rebirth uses one synchronous PostgreSQL repository through
  SQLAlchemy and `psycopg`; SQLite is restricted to isolated test processes.
- Auth sessions, collection, progression, boosters, immutable ledger, wallet,
  market, achievements and authoritative authenticated match state live in the
  same versioned schema.
- Real-money Coinz/Gemas acquisition is disabled until official store receipt
  validation exists. The player market uses Ouro only.
- Account reset emits compensating ledger movements and never erases economic
  history. Tutorial and clash rewards use one-time persistence keys.

Operational gates:

- Render runs `python -m services.rebirth_schema upgrade` before application
  startup and `/health` validates schema version and connectivity.
- PostgreSQL contention and restart tests run under the
  `requires_postgres` marker with a real Postgres container in CI.
- Asset delivery uses WebP, limited precache and a native mobile arena with
  explicit touch-size tests.
