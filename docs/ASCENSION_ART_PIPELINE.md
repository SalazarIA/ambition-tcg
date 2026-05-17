# Ascension Art Pipeline

Assets live under `static/assets/ascension/`:

- `cards/`
- `champions/`
- `ui/`
- `manifest.json`

## Naming

- Cards: `cards/<card_id>.webp`
- Champions: `champions/<champion_id>.webp`
- UI assets: `ui/<component-name>.svg`

## Recommended Sizes

- Card frames: 768x1075
- Champion portraits: 1024x1024
- UI glyphs: 512x512 SVG or transparent PNG/WebP

## Style Direction

Obsidian base, ritual geometry, ember-gold accents, premium negative space, readable silhouettes and no generic fantasy template panels.

## Placeholders

The current manifest records placeholder paths only. The UI remains code-native and uses initials/runes until real art is added.

## Adding Real Art Later

Add the asset file, update `manifest.json`, then wire the card or Champion id to the new path. Do not change gameplay payloads just to add art.
