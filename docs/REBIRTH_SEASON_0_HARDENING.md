# Rebirth Season 0 Architecture Hardening

This document merges the local code audit with
`/Users/lucassilverio/Downloads/relatorio_tcg_online_ambitionz.pdf`.

## What The PDF Asked For

The report's core recommendation is not "add random features". It says a serious
online TCG needs:

- server-authoritative resolution;
- deterministic match state;
- commands and events;
- public/private serialization;
- auth, collection, loadout, rewards and shop persistence;
- economy ledger instead of only balances;
- match history;
- support/admin tooling;
- PWA cache hygiene;
- balance simulation;
- a locked product identity.

## What Rebirth Already Had

Before this hardening block, Rebirth already had:

- Flask + vanilla frontend;
- server-side match resolution;
- active Rebirth routes and legacy retirement guards;
- SQLite auth, collection, loadout, boosters, progression and achievements;
- CSRF, headers and auth throttling;
- 13-card starter set with PNG art and engine-backed ability keys;
- three bot personalities;
- PWA manifest/service worker;
- pytest release gate scoped to `tests/rebirth`.

## What Was Added In This Block

- `services/rebirth_events.py` with command/event append helpers, match
  versioning, state hash and compact snapshots.
- Public match state now includes `version`, `state_hash` and recent `events`.
- `PLAY_CARD`, `EVOLVE_DUPLICATE` and `NEXT_TURN` commands are recorded.
- Server consequences now emit events such as `CARD_PLAYED`, `CARD_EVOLVED`,
  `CLASH_RESOLVED`, `DAMAGE_DEALT`, `ABILITY_TRIGGERED`, `TURN_STARTED` and
  `MATCH_FINISHED`.
- Signed-in matches persist to `match_history`, `match_commands` and
  `match_events`.
- Rewards, starter cards, booster cards, daily XP, tutorial XP and admin grants
  write `economy_ledger` entries.
- `/rebirth/history` and `/api/rebirth/match-history` expose match history.
- `/api/rebirth/match-history/<match_id>/events` exposes replay source events.
- `/api/rebirth/economy-ledger` exposes economy movement history.
- `/rebirth/support`, `/api/rebirth/support/export` and
  `/api/rebirth/support/reset` provide self-service support.
- `/api/rebirth/admin/grant` provides token-protected admin grants through
  `REBIRTH_ADMIN_TOKEN`.
- Balance Lab now evolves player duplicates and picks tactical lines using the
  active engine.
- `tools/rebirth_balance_report.py` generates
  `docs/REBIRTH_BALANCE_REPORT.md`.
- The service worker cache moved to `ambitionz-rebirth-season0-v30`.
- `static/js/pwa.js` now exposes an update prompt for waiting service workers.
- Active UI copy no longer says "Prototype" on the main Rebirth CTA.

## Current Truth

Rebirth is now a more professional MVP foundation:

- The frontend renders state and sends intent.
- The backend validates and resolves rules.
- The engine emits consequences.
- The database records account ownership, reward movement and match history.
- The old product remains retired.

## Still Not Complete

These are intentionally not claimed as done:

- real multiplayer;
- real-time reconnect;
- durable live match storage;
- production backup/restore automation;
- payment processor;
- seasons, ranked ladder or weekly events;
- committed screenshot visual baselines;
- production analytics/monitoring.

## Validation

Current validation for this block:

```text
python3 -m pytest -q
66 passed

node --check static/js/rebirth.js
node --check static/js/service-worker.js
node --check static/js/pwa.js
node --check static/js/rebirth_product.js
passed
```
