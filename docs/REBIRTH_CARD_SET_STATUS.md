# Rebirth Card Set Status

## Product Decision

Rebirth 021 finishes the first active card set before adding more product
systems. The starter set is intentionally small, readable and engine-backed.
No legacy Arena, Ascension, BE2 or old collection/deck-builder rules were
restored.

## Active Card Contract

Every active Rebirth card must have:

- unique `id`;
- `ability_key`, `ability_name` and `ability_text`;
- attack, guard, element, role, tier and family;
- PNG art under `static/assets/rebirth/cards/*-art.png`;
- matching art profile in `services/rebirth_art.py`;
- matching manifest entry in `static/assets/rebirth/manifest.json`;
- engine behavior covered by `tests/rebirth/test_rebirth_card_set.py`.

Current art version:

```text
rebirth-021
```

## Base Monsters

- `dreadclaw` - Rending Strike: wounded-target finisher pressure.
- `stoneshell` - Brace: low-attack guardian that reduces incoming damage.
- `shadewisp` - Fade Cut: tie-break assassin against wounded targets.
- `skywarden` - High Guard: gains clash attack into low-guard cards.
- `ironbastion` - Bulwark: absorbs low-attack incoming damage.
- `embermaw` - Molten Bite: high-pressure damage bonus.
- `voidstalker` - Silent Pursuit: early-turn clash pressure.

## Evolutions

- `dreadmaw` from Dreadclaw - stronger wounded-target finisher.
- `stonewarden` from Stoneshell - heavy damage reduction and counter damage.
- `nightfang` from Shadewisp - tier 2 shadow finisher.
- `stormwarden` from Skywarden - punishes low guard with dive damage.
- `ironbulwark` from Ironbastion - fortress reduction and minimum damage.
- `embermaw_alpha` from Embermaw - clean fire finisher.

Evolved cards are tier 2 and are not present in the default player or bot deck.
They enter play through duplicate evolution or no-payment booster ownership.

## Validation

Required card gate:

```bash
python3 -m pytest tests/rebirth/test_rebirth_card_set.py -q
```

Full active suite after Season 0 hardening:

```text
66 passed
```

## Current Limits

- Clash feedback now surfaces ability events, card impact pulses and optional
  lightweight haptic/audio cues in capable browsers.
- Balance telemetry is available through deterministic local simulation, but it
  is not persisted as live production analytics yet.
- Bot personality tuning now has defensive, aggressive and opportunist profiles;
  further numeric tuning should use Balance Lab output and real playtest notes.
