# Ambitionz Rebirth Visual Standard

## Pattern Name

Ambitionz Rebirth Premium Clash UI

## Visual Principles

- Mobile-first card battler interface.
- One central decision at a time.
- Premium dark surface with restrained metal and glass texture.
- Player language uses gold and amber.
- Bot language uses blue and cyan.
- The main monster card is the visual anchor.
- The reference portrait board is locked at `852px x 1846px` and scaled with `min(viewportWidth / 852, viewportHeight / 1846)`.
- The main card is centered inside the board and the duplicate panel is attached as a right-side rail.
- Secondary panels stay compact and subordinate to the card.
- Card art is a first-class asset and must not fall back to generic empty placeholders or flat line-art substitutes.
- Text is direct, short and readable in under 15 seconds.
- Motion and state changes should clarify selection, evolution and clash results.

## Official Palette

- Page black: `#030405`
- Raised black: `#07090c`
- Panel black: `rgba(14, 17, 21, 0.94)`
- Player gold: `#f4ad26`
- Player bright gold: `#ffc852`
- Bot cyan: `#58d6ff`
- Text ivory: `#f1f1ef`
- Muted text: `#a5a5a2`
- Defeat red: `#ff7e66`
- Victory green: `#82f0b1`

## Mobile Layout Hierarchy

1. Fixed game viewport with no document scroll.
2. Scaled `852px x 1846px` game board.
3. Top HUD with player mark, YOU, HP 30 bar, TURN and BOT HP bar.
4. Two slogan blocks:
   - One card.
   - One decision.
   - One clash.
   - Combine duplicates.
   - Evolve monsters.
   - Win the duel.
5. Bot card zone, face down before reveal.
6. Large main card stage.
7. Duplicate and evolution panel.
8. Horizontal player hand.
9. Primary CLASH action and secondary COMBINE or NEXT TURN action.
10. Result panel.
11. Compact turn log.
12. Play Rebirth Prototype CTA and New Match control.

## Required Components

- `rb-game-viewport` fixed viewport.
- `rb-game-board` scaled board.
- `rb-clash-shell` compatibility app shell class.
- `rb-hud` top HUD.
- `rb-slogan-grid` hero slogans.
- `bot-card` bot card zone.
- `focus-card` large central card.
- `evolution-panel` duplicate/evolution panel.
- `player-hand` horizontal mini card hand.
- `play-button` primary CLASH button.
- `evolve-button` COMBINE button.
- `next-turn-button` secondary next-turn action.
- `result-label`, `result-title`, `result-copy` result messaging.
- `turn-log` compact log.
- `player-hp-fill` and `bot-hp-fill` HP bar fills.
- `evolution-card-thumbnail` duplicate thumbnail.
- `rb-asset-fallback` premium fallback state.

## Prohibited Changes

- Do not add lanes.
- Do not add a multi-card field.
- Do not add old Arena, BE2, Ascension, Collection, Deck Builder, Shop, Gold, Missions, Ranking or Progression UI.
- Do not add generic neon, purple fantasy glow or old Ambitionz beta styling.
- Do not turn the MVP into a traditional TCG board.
- Do not load old CSS or old JS on `/` or `/rebirth`.
- Do not allow document/body scroll on `/rebirth`.
- Do not hide the main card behind dashboards, modals or dense panels.

## Rules For Future Changes

- Keep every new interaction centered on one card, one response and one clash.
- Keep HP, attack, guard and ability text visible in the card battler hierarchy.
- Preserve the gold player and cyan bot language.
- Keep cards, HUD and buttons readable on a 390px mobile viewport.
- Keep the 852px reference composition visually comparable to the approved mock before changing card, HUD or action sizing.
- Prefer fewer, stronger components over extra panels.
- Any new route or feature must keep `/health`, `/` and `/rebirth` stable.
- Any new frontend code must preserve the JS IDs listed in Required Components.
- Visual polish must improve the approved pattern, not replace it.

## Visual QA Checklist

- `/rebirth` loads without old assets.
- `/rebirth` has no document scroll and wheel does not change `scrollY`.
- The scaled board fits entirely inside 390x844, 852x1846, 1440x900 and 2048x1218 viewports.
- The first mobile viewport shows HUD, slogans, bot card and main card.
- The hand scrolls horizontally without page overflow.
- CLASH is the dominant gold action.
- COMBINE appears when a duplicate evolution is available.
- Selected hand card has a clear gold frame and raised state.
- Bot card uses cyan framing.
- Main cards show name, role, art, ability, attack and guard.
- Victory, Defeat and Clash results are visually distinct.
- Turn log remains compact.
- Desktop view keeps the same hierarchy without adding lanes.
- Desktop view centers the main card itself, not the combined card-plus-side-panel group.
- The Dreadclaw hero card uses the approved raster art asset, and the bot back/emblem use the approved reference assets.
- Text does not overlap cards, buttons or HUD.
- Service worker cache lists only active Rebirth assets.
