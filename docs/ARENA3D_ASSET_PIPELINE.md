# Ambitionz Arena 3D Asset Pipeline

Runtime assets ship as GLB or glTF 2.0. Source files can live in Blender or another DCC tool, but browser code should only depend on stable manifest keys from `static/assets/arena3d/manifest.json`.

## Export Rules

- Apply transforms before export.
- Use meters, Y-up, and table center at world origin.
- Keep pivots useful for gameplay: cards pivot at center, tokens at floor contact, FX at impact origin.
- Name important nodes with stable semantic names such as `slot_player_monster`, `token_creature`, or `fx_strike_core`.
- Keep collision proxies separate and named with `collision_` when physics is introduced.

## Optimization

Run optimization after every GLB export:

```bash
npm run arena3d:assets:optimize -- static/assets/arena3d/models/source.glb static/assets/arena3d/models/output.glb
```

Inspect assets before shipping:

```bash
npm run arena3d:assets:inspect
```

Default budgets:

- Initial 3D scene: under 900 KB gzip.
- Individual gameplay model: target 12k triangles or less.
- Textures: 1024 px max until a card or arena truly needs more.
- Draw calls: target under 80 in normal play.

## First Asset Targets

1. `arena_default.glb`: table, board lanes, center divider.
2. `card_back_default.glb`: reusable card back plane with bevel.
3. `token_creature.glb`: simple creature marker.
4. `token_support.glb`: support marker.
5. `fx_strike.glb`, `fx_guard.glb`, `fx_focus.glb`: lightweight animated or static FX anchors.

The current renderer has procedural fallbacks, so missing GLBs should not block development.
