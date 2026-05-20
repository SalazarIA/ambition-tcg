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
- `GET /api/rebirth/shell` returns the product shell summary.
- `GET /api/rebirth/session` returns the active Rebirth account session.
- `GET /api/rebirth/csrf` returns the current session CSRF token.
- `POST /api/rebirth/auth/register` creates a Rebirth account and starter
  ownership.
- `POST /api/rebirth/auth/login` signs in an existing Rebirth account.
- `POST /api/rebirth/auth/logout` clears the Rebirth session.
- `POST /api/rebirth/auth/change-password` updates the signed-in account
  password after current-password verification.
- `GET /api/rebirth/auth-plan` returns the Rebirth-native auth plan.
- `GET /api/rebirth/collection` returns account collection/loadout state.
- `POST /api/rebirth/loadout` validates and persists an eight-card account
  loadout.
- `GET /api/rebirth/shop` returns the no-payment shop payload and booster
  history.
- `POST /api/rebirth/booster/open` opens a no-payment booster and persists
  ownership for the signed-in account.
- `GET /api/rebirth/progression` returns the progression/reward state.
- `GET /api/rebirth/profile` returns profile stats, achievements and recent
  booster context.
- `POST /api/rebirth/progression/claim-daily` claims the current daily reward.
- `GET /api/rebirth/desktop` returns the desktop arena polish notes.
- `GET /api/rebirth/onboarding` returns tutorial state.
- `POST /api/rebirth/onboarding/complete` persists tutorial completion.
- `GET /api/rebirth/balance/simulate` returns a deterministic balance report.
- `GET /api/rebirth/release` returns the release hygiene checklist.

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

The product-shell frontend renders server-provided payloads, signs users in,
persists loadouts through `/api/rebirth/loadout`, opens no-payment boosters
through `/api/rebirth/booster/open`, claims rewards, completes onboarding and
changes signed-in passwords. Mutating Rebirth requests send
`X-Rebirth-CSRF`.

The frontend does not compute gameplay outcomes.
