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
