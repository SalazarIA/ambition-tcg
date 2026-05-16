# Ambitionz Card Art Direction

Ambitionz card art uses a premium fantasy neon look: deep violet backgrounds, arcane cyan light, gold highlights and clear silhouettes that still read on a mobile card.

## Core Identity

- Original fantasy TCG art, no borrowed IP, no named third-party worlds, no living artist style references.
- High readability first: the card name, type, cost and element must remain legible over every art treatment.
- Card frames may glow, but the frame should not overpower the tactical information.
- Placeholders are official beta placeholders, not broken assets.

## Element Palettes

- Fire: red, orange, gold, sparks, pressure and direct damage.
- Water: blue, cyan, reflection, flow, focus and light sustain.
- Earth: dark green, stone, bronze, armor, defense and durable bodies.
- Plant: vivid green, bioluminescence, roots, growth and control.
- Global or Neutral: violet, silver, cyan, arcane geometry and flexible utility.
- Shadow if introduced: dark violet, smoke, distortion and risk.
- Light if introduced: gold, white, radiant lines and protection.

## Rarity Frames

- Common: clean frame, low glow, readable silhouette.
- Uncommon: colored edge, moderate aura and extra border detail.
- Rare: stronger glow, sharper runes and more dramatic lighting.
- Epic: animated or high-energy aura when motion is allowed.
- Legendary: gold/cyan/magenta aura, strongest frame detail, still readable.

## Prompt Rules

Every prompt should include:

- Card name, type, element and rarity.
- Original creature or spell design.
- Clear composition with one central subject.
- Palette tied to element identity.
- "premium fantasy neon trading card illustration, original creature design, high readability, mobile-first card art".
- Negative prompt: no text, no logo, no watermark, no third-party characters, no copied franchise style.

## Asset Naming

- Store final art under `static/assets/cards/generated/`.
- Use lowercase card ids as file names, for example `fire_001.png`.
- Keep placeholders under `static/assets/cards/placeholders/`.
- Update `static/assets/cards/card_art_manifest.json` when adding final art.
- RC V6 starter entries also include `role`, `simple_use_text` and `short_lore` so the Arena, Collection and Deck Builder can teach how the card is used before final art exists.

## QA

Run:

```bash
python3 tools/qa/card_art_manifest_check.py
```

The manifest checker validates required fields, duplicate ids, placeholder state and missing files for non-placeholder art.
It also validates that the 30 BE2 starter cards include role and how-to-use identity fields.
