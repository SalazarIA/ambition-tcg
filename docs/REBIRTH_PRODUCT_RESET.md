# Ambitionz Rebirth Product Reset

Ambitionz Rebirth exists because the old product surface became too layered to keep polishing as the main global experience. Arena V48, BE2, economy beta, legacy collection, shop experiments, roadmap pages, tutorial loops, service worker revisions and early 3D experiments all carry useful work, but together they make the product feel patched instead of born from one clear design.

Rebirth is the clean laboratory for the next Ambitionz core.

## Why Rebirth Exists

- The main product needs one readable tactical fantasy: one active card, one will, one decisive clash.
- The old Arena grew around lanes, dense HUD, socket state and visual compromises that no longer match the target product.
- The future 3D arena needs its own contract instead of being a decorative background behind legacy UI.
- Product, gameplay, state payload and visual language need to move together.

## Retired Legacy Surface

The old product is not deleted from the repository, but it is retired from the
active runtime. These routes and systems are historical only:

- `/training-legacy`
- `/arena`
- BE2 and socket flows
- old collection and deck builder
- economy beta, shop, missions, daily, profile and match history
- Arena V48 assets

Retired browser routes now redirect to `/rebirth`. Retired API groups now return
`410 legacy_disabled`. They should not be reactivated unless a future product
decision explicitly moves a feature into Rebirth-native contracts.

## New Product Surface

`/rebirth` is the isolated laboratory for Ambitionz Rebirth. It owns:

- one-card active gameplay
- Rebirth-specific state contract
- premium `rb-*` UI language
- Rebirth 3D adapter boundary
- defensive JSON APIs
- Rebirth tests and QA smoke

## Why Arena V48 Is Not The Main Polish Target

Arena V48 is valuable as history and fallback, but it is not the shape of the future product. It carries lane assumptions, legacy taxonomy, old HUD density and too many compatibility layers. Rebirth avoids sanding that old surface again and creates a smaller, stronger foundation.

## Product Rule

No three-lane board exists in Rebirth. Each player controls one active card. The next product iterations should deepen that rule rather than reintroduce a crowded field.

See `docs/LEGACY_CLEANUP_MAP.md` for the current route/file ownership map between Rebirth, legacy and shared surfaces.

## Forward Product Path

Rebirth is now the forward product path for new Ambitionz gameplay and presentation work. Legacy Arena remains repository history and QA reference material, not an active runtime product.

## Product Migration Phases

- Phase 1: parallel prototype. Complete.
- Phase 2: Rebirth playable alpha. Complete.
- Phase 3: Rebirth public home. Complete.
- Phase 4: legacy retirement. Active: browser routes redirect, legacy APIs return `410 legacy_disabled`, historical tests live under `tests/legacy_disabled`.

## Route Promotion Plan

Current:

- `/rebirth` is the active playable product path.
- Home is Rebirth-first.
- Legacy browser routes redirect to `/rebirth`.
- Legacy API groups return `410 legacy_disabled`.

Next:

- Migrate useful collection, deck, rewards and progression behavior into Rebirth-native contracts.
- Keep old files and tests as historical reference only.

Future:

- `/play` can redirect to `/rebirth`.
- Add Rebirth-native persistence and progression after the MVP state contract is stable.
