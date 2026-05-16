# Starter Deck Teaching Pass

RC V6 keeps the BE2 beta starter deck fixed at 30 cards and uses it as the first playable lesson. The deck should teach the player how Creature, Spell, Trap and Strategy choices interact before any advanced collection work is required.

## Current Shape

- Total cards: 30.
- Creatures: 21.
- Spells: 6.
- Traps: 3.
- Max copies: handled by deck validation, currently capped by the beta rule.
- Curve: mostly cost 1-3 so the first hand is playable.

## Teaching Goals

- Fire creatures teach pressure and direct lane pressure.
- Earth creatures teach durable bodies and defensive turns.
- Water creatures teach Ambition and resource planning.
- Plant creatures teach utility/control and stabilizing lanes.
- Damage spells teach target selection and immediate pressure.
- Shield/heal spells teach defensive timing.
- Ambition spells teach why Focus matters.
- Counter and defense traps teach prepare-now, trigger-later gameplay.

## Starter Identity Roles

The 30 starter cards are annotated in `static/assets/cards/card_art_manifest.json` with:

- `role`
- `simple_use_text`
- `short_lore`
- `visual_identity`
- refined `prompt`
- refined `fallback_gradient`

The UI can show these fields in the Arena, Collection and Deck Builder without requiring final card art.

## QA Expectations

- Starter deck remains 30 cards.
- Starter deck contains Creature, Spell and Trap cards.
- First hand must not hard-lock the player.
- Battle simulation must complete without integrity errors.
- Manifest check must confirm the 30 starter card identity fields are present.

## Known Limits

- The starter deck is still a beta teaching deck, not a final competitive list.
- Final art files are not required; placeholder/fallback art remains the source of truth for this RC.
- Post-deploy telemetry is required to confirm whether players actually use Guard, Focus, Spells and Traps more often.

