# Rebirth UI Contract

The Rebirth frontend consumes a stable JSON payload from `/api/rebirth/*`.

## Public State Shape

```json
{
  "match_id": "rebirth-...",
  "phase": "INTENT",
  "round": 1,
  "player": {
    "name": "Player",
    "hp": 30,
    "ambition": 0,
    "active_card": null,
    "hand": [],
    "selected_intent": null
  },
  "opponent": {
    "name": "Opponent",
    "hp": 30,
    "ambition": 0,
    "active_card": null,
    "selected_intent": null
  },
  "active_card": null,
  "hand": [],
  "available_actions": [],
  "selected_intent": null,
  "combat_log": [],
  "cinematic_event": null,
  "ui_flags": {
    "can_resolve": false,
    "can_play_card": true,
    "is_finished": false
  },
  "winner": null,
  "is_finished": false
}
```

## Rules

- Decks are never sent to the browser.
- Player hand is public to the player.
- Opponent hand and deck are hidden.
- `combat_log` returns the latest 12 entries.
- Cards use `compact_card`.
- `available_actions` is a list of stable action dictionaries.

## Frontend Responsibilities

The frontend renders the state, sends player actions through fetch, disables invalid buttons, and forwards cinematic events to `window.Rebirth3D`.
