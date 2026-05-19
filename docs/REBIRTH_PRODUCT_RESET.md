# Ambitionz Rebirth Product Reset

Ambitionz Rebirth exists because the old product surface became too layered to keep polishing as the main global experience. Arena V48, BE2, economy beta, legacy collection, shop experiments, roadmap pages, tutorial loops, service worker revisions and early 3D experiments all carry useful work, but together they make the product feel patched instead of born from one clear design.

Rebirth is the clean laboratory for the next Ambitionz core.

## Why Rebirth Exists

- The main product needs one readable tactical fantasy: one active card, one will, one decisive clash.
- The old Arena grew around lanes, dense HUD, socket state and visual compromises that no longer match the target product.
- The future 3D arena needs its own contract instead of being a decorative background behind legacy UI.
- Product, gameplay, state payload and visual language need to move together.

## Frozen Legacy Surface

The old product is not deleted. These routes and systems remain available:

- `/training-legacy`
- `/arena`
- BE2 and socket flows
- old collection and deck builder
- economy beta, shop, missions, daily, profile and match history
- Arena V48 assets and service worker compatibility entries

They are frozen as legacy/internal surfaces unless a future migration block explicitly upgrades them.

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

Rebirth is now the forward product path for new Ambitionz gameplay and presentation work. Legacy Arena remains available for compatibility, QA comparison and internal fallback, but new product development should prefer `/rebirth` unless the task explicitly maintains legacy.

## Product Migration Phases

- Phase 1: parallel prototype. Rebirth ships beside the old Arena without breaking existing routes.
- Phase 2: Rebirth playable alpha. The one-card loop, premium shell, browser contract, QA smoke and 3D adapter become the active prototype foundation.
- Phase 3: Rebirth public home. The main landing surface can promote Rebirth as the product lead once onboarding, balance and visual QA mature.
- Phase 4: legacy retirement. Arena V48 and BE2 can be hidden or retired only after data, QA and user-facing migration prove the replacement stable.

## Route Promotion Plan

Current:

- `/rebirth` is the primary alpha path.
- Home points to Rebirth first.
- Legacy surfaces remain available and clearly marked.

Next:

- Migrate useful collection, deck, rewards and progression behavior into Rebirth-native contracts.
- Keep legacy banners on old beta surfaces during migration.
- Continue using `/training-legacy` and old Arena only for compatibility checks.

Future:

- `/play` can redirect to `/rebirth`.
- `/training` can become legacy-only or redirect after Ascension compatibility is retired.
- Old `/arena` can move to archived/internal access after Rebirth has account persistence and QA coverage.
