# Rebirth UI Contract

The active Rebirth frontend consumes JSON from the current `/api/rebirth/*`
endpoints only. Older deck, intent, resolve, restart and 3D adapter contracts
are historical and are not active runtime APIs.

## Public State Shape

```json
{
  "match_id": "rebirth-...",
  "architecture": "Ambitionz Rebirth",
  "turn": 1,
  "phase": "choose",
  "player": {
    "name": "You",
    "hp": 30,
    "max_hp": 30,
    "deck_count": 11,
    "discard_count": 0,
    "played_card": null,
    "wounded": false,
    "hand": []
  },
  "bot": {
    "name": "Bot",
    "hp": 30,
    "max_hp": 30,
    "deck_count": 11,
    "discard_count": 0,
    "played_card": null,
    "wounded": false,
    "hand_count": 5
  },
  "available_evolutions": [],
  "last_clash": null,
  "result": null,
  "winner": null,
  "is_finished": false,
  "log": []
}
```

## Active API

- `POST /api/rebirth/start` starts an in-memory match.
- `POST /api/rebirth/play-card` resolves the chosen player card against the
  bot response.
- `POST /api/rebirth/evolve` combines two matching base monsters into one
  evolved card when available.
- `POST /api/rebirth/next-turn` advances from `result` to `choose`.

## Retired API

The following former Rebirth productization endpoints are not active:

- `/api/rebirth/decks`
- `/api/rebirth/decks/<deck_id>`
- `/api/rebirth/new`
- `/api/rebirth/intent`
- `/api/rebirth/resolve`
- `/api/rebirth/restart`

Do not recreate them unless a future Rebirth-native feature explicitly needs
them.

## Rules

- Deck lists are never sent to the browser.
- Player hand is public to the player.
- Bot hand is hidden and represented by `hand_count`.
- `log` returns the latest entries needed by the current UI.
- Cards must include art metadata: `art`, `art_key`, `art_status`,
  `art_version`, `palette` and `silhouette`.
- Expected player/request mistakes return JSON errors, not 500s.

## Frontend Responsibilities

The frontend renders server state, sends player actions through fetch, disables
invalid buttons, preloads active Rebirth art and keeps `/rebirth` locked as a
single-screen board.

The frontend does not compute gameplay outcomes.
