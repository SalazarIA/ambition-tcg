# Rebirth UI Contract

The Rebirth frontend consumes a stable JSON payload from `/api/rebirth/*`.

## Public State Shape

```json
{
  "match_id": "rebirth-...",
  "phase": "INTENT",
  "round": 1,
  "selected_deck_id": "ember_oath",
  "selected_deck_name": "Ember Oath",
  "difficulty": "normal",
  "difficulty_label": "Normal",
  "opponent_profile": {
    "id": "warden",
    "name": "The Warden",
    "style": "Defensive",
    "description": "A defensive rival profile."
  },
  "player": {
    "name": "Player",
    "hp": 32,
    "ambition": 0,
    "active_card": null,
    "hand": [],
    "selected_intent": null
  },
  "opponent": {
    "name": "Opponent",
    "hp": 32,
    "ambition": 0,
    "active_card": null,
    "selected_intent": null
  },
  "active_card": null,
  "hand": [],
  "available_actions": [],
  "selected_intent": null,
  "combat_log": [],
  "cinematic_event": {
    "type": "DAMAGE",
    "title": "Damage Lands",
    "message": "Opponent takes 6 damage.",
    "intensity": "high",
    "payload": {},
    "round": 1
  },
  "ui_flags": {
    "can_resolve": false,
    "can_play_card": true,
    "has_active_card": false,
    "has_selected_intent": false,
    "needs_active_card": true,
    "is_finished": false
  },
  "match_summary": null,
  "reward_preview": null,
  "winner": null,
  "is_finished": false
}
```

## Deck API

- `GET /api/rebirth/decks` returns compact deck cards for selection UI.
- `GET /api/rebirth/decks/<deck_id>` returns deck detail and compact cards.
- `GET /api/rebirth/new?deck_id=ember_oath&difficulty=normal` starts a configured match.
- `POST /api/rebirth/restart` accepts `deck_id` and `difficulty`.

## Rules

- Decks are never sent to the browser.
- Player hand is public to the player.
- Opponent hand and deck are hidden.
- `combat_log` returns the latest 12 entries.
- Cards use `compact_card`.
- `available_actions` is a list of stable action dictionaries.

## Frontend Responsibilities

The frontend renders the state, sends player actions through fetch, disables invalid buttons, and forwards cinematic events to `window.Rebirth3D`.

It also owns local-only preferences for:

- `ambitionz_rebirth_selected_deck`
- `ambitionz_rebirth_difficulty`
- `ambitionz_rebirth_onboarding_seen`
