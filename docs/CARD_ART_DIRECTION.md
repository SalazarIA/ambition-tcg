# Ambitionz Card Art Direction

Ambitionz card art now follows the dark fantasy premium direction defined in `docs/AMBITIONZ_VISUAL_BIBLE.md`: ancient stone, aged metal, parchment, restrained magic light and clear silhouettes that read on a mobile card. Neon may appear only as controlled spell light or rune feedback, never as the whole product identity.

## Core Identity

- Original fantasy TCG art, no borrowed IP, no named third-party worlds, no living artist style references.
- High readability first: the card name, type, cost and element must remain legible over every art treatment.
- Card frames use aged metal, stone, parchment and restrained magical accents; the frame should not overpower tactical information.
- Placeholders are official beta placeholders, not broken assets.

## Element Palettes

- Fire: dark ember, copper, lava orange, gold sparks, pressure and direct damage.
- Water: deep blue stone, cyan reflection, silver rune light, focus and light sustain.
- Earth: moss stone, bronze armor, muted green, defense and durable bodies.
- Plant: root green, living vine light, amber sap, growth and control.
- Global or Neutral: smoky violet, tarnished silver, old arcane parchment and flexible utility.
- Shadow if introduced: dark violet, smoke, distortion and risk.
- Light if introduced: gold, white, radiant lines and protection.

## Rarity Frames

- Common: clean aged-metal frame, low glow, readable silhouette.
- Uncommon: colored edge, moderate rune accent and extra border detail.
- Rare: stronger metal/rune contrast, sharper silhouette and more dramatic lighting.
- Epic: controlled magical aura when motion is allowed.
- Legendary: gold and old arcane light, strongest frame detail, still readable.

## Prompt Rules

Every prompt should include:

- Card name, type, element and rarity.
- Original creature or spell design.
- Clear composition with one central subject.
- Palette tied to element identity.
- "dark fantasy premium Ambitionz trading card illustration, original creature or spell design, high readability, mobile-first card art".
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
