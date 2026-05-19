# Rebirth 3D Model Contract

The Rebirth arena 3D layer is not a background. It is its own product layer with a stable event boundary.

## Layer Model

- Gameplay state lives in Python services.
- DOM UI owns readable controls, cards and logs.
- `rebirth_3d_adapter.js` owns the bridge to the arena scene.
- Future Three.js/GLB work plugs into the adapter.

## Adapter Events

The adapter receives:

- `rebirth:match_start`
- `rebirth:intent_selected`
- `rebirth:card_activated`
- `rebirth:strike`
- `rebirth:guard`
- `rebirth:focus`
- `rebirth:damage`
- `rebirth:ko`
- `rebirth:round_end`

## Manifest

`static/assets/rebirth3d/manifest.json` contains placeholder keys:

- `arena_core`
- `player_avatar`
- `opponent_avatar`
- `active_card_frame`
- `strike_fx`
- `guard_fx`
- `focus_fx`
- `ambition_fx`

No GLB is required in this block. Null values are valid placeholders until real assets are authored.

## Future Asset Policy

When real 3D assets arrive, use stable manifest keys rather than hard-coded filenames. GLB or glTF 2.0 should be the default shipping format.
