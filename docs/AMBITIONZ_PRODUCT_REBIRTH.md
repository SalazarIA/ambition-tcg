# Ambitionz Product Rebirth

Ambitionz is moving from the legacy lane-based fantasy TCG prototype into a new main product: **Ascension Duel**. The old model proved useful for beta validation, but it made the product read like a generic card battler and forced the UI to spend attention on slots, lanes and board management instead of the emotional center of Ambitionz: ambition, pressure, vows, sacrifice and domination.

## Why the Old Main Model Is Retired

- The three-slot lane surface made every match look like a familiar prototype board.
- Monsters, spells and traps carried genre baggage that diluted the Ambitionz identity.
- The old Arena required dense HUDs, target markers and board state explanations before the player could feel the duel.
- Mobile readability suffered because the main screen tried to show too many simultaneous objects.
- The product needed a global-ready loop with fewer generic terms and a stronger ownable visual shape.

The legacy BE2 and old Arena files remain available for fallback and internal comparison. They are no longer the default Training product surface.

## New Main Product

The canonical combat architecture is **Ascension Duel**:

- One active **Champion** per side.
- Champions may be Summoned, Bound as Souls, Burned into Echo or Ascended.
- Techniques are direct actions.
- Relics are persistent modifiers.
- Schemes are hidden or prepared effects.
- Ascensions convert accumulated Ambition into ultimate pressure.
- The central resource is the **Ambition Core**.
- Rounds resolve through a psychological **Mind Clash** driven by Intent.

## Main Terms

- Board becomes **Duel Altar**.
- Lane is removed from the main experience.
- Monster becomes **Champion**.
- Graveyard becomes **Echo**.
- Spell becomes **Technique**.
- Trap becomes **Scheme**.
- Attachment or buff becomes **Bound Soul**.
- Ultimate becomes **Ascension** or **Domination**.
- Turn becomes **Round**.
- Ready becomes **Commit**.
- Battle log becomes **Chronicle**.

## Product Contract

`/training` is now the Ascension Duel entry point. `/training-legacy` preserves the old lane-based Arena. Existing economy, collection, deck, missions, profile, feedback, telemetry, sockets and public beta systems remain in place until their contracts are migrated.

New canonical files:

- `services/ascension_cards.py`
- `services/ascension_engine.py`
- `services/ascension_bot.py`
- `services/ascension_payloads.py`
- `services/ascension_progression.py`
- `templates/arena_ascension.html`
- `static/css/ambitionz_ascension.css`
- `static/js/ambitionz_ascension.js`

## Launch Shape

The new surface is mobile-first, dark, ritualistic and focused. The player should feel one Champion, one rival, a visible Ambition Core and a decisive pressure line before they read any rule text.
