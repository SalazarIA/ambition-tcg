# Ascension Frontend Architecture

Ambitionz public product pages now share the `ax-` Ascension shell. The goal is visual consistency across Home, Arena, Collection, Deck Builder, Chronicle, Roadmap and Tutorial without copying isolated page hacks.

## Shared Shell

- `ax-body` owns the obsidian background, ritual geometry and global type color.
- `ax-shell` constrains content width and keeps safe-area padding consistent.
- `ax-product-shell` is the standard non-combat page shell.
- `ax-arena-shell` is the viewport-bound combat shell.
- `ax-topbar`, `ax-brand`, `ax-title-block` and `ax-top-actions` define navigation.

## Design Tokens

Tokens live in `static/css/ambitionz_ascension.css` under `:root`.

- Background: `--ax-bg`, `--ax-bg-2`, `--ax-bg-3`
- Panels: `--ax-panel`, `--ax-panel-strong`, `--ax-panel-soft`
- Borders: `--ax-border`, `--ax-border-strong`, `--ax-line`
- Accents: `--ax-gold`, `--ax-gold-soft`, `--ax-ember`
- State: `--ax-danger`, `--ax-success`
- Spacing: `--ax-space-1` through `--ax-space-6`
- Radius: `--ax-radius-xs`, `--ax-radius-sm`, `--ax-radius`, `--ax-radius-lg`
- Shadows: `--ax-shadow-sm`, `--ax-shadow`, `--ax-shadow-gold`
- Typography: `--ax-type-xs` through `--ax-type-hero`
- Viewport: `--ax-viewport-shell`, `--ax-viewport-header`, `--ax-viewport-status`, `--ax-viewport-hand`, `--ax-viewport-actions`

## Product Route Contract

Public Ascension routes should lead with Champion, Technique, Relic, Scheme, Ascension, Duel Altar, Ambition Core, Chronicle, Commit and Round. Legacy route names are not primary navigation. `/training-legacy` remains an explicit fallback only.

## Maintainability Rule

New public product surfaces should use the shared `ax-` shell first. Page-specific classes are allowed only to describe layout intent, such as `ax-home-hero`, `ax-page-grid` or `ax-chronicle-compact`.
