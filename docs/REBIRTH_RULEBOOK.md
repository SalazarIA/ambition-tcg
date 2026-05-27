# Ambitionz Rebirth Rulebook

Ambitionz Rebirth is the active Ambitionz TCG runtime: a server-authoritative
duel played on two three-slot battlefields, with a PvE campaign and persistent
collection loop.

## Core Loop

1. Standard arena duels begin with 30 HP on each side and a five-card hand.
2. The guided first duel keeps the player at 30 HP and sets the novice bot to
   18 HP; early follow-up duels use the defensive bot learning curve.
3. Each side owns three persistent battlefield slots. Monsters remain on the
   field until destroyed or consumed by fusion.
4. During `choose`, the player can summon a monster, play a spell, arm a trap,
   evolve duplicate cards from hand, fuse eligible field units or attack with
   a ready monster.
5. Monsters spend mana when summoned. Energy refills each turn on a ramp from
   2 through 10.
6. A targeted attack damages the defender's Guarda. Damage exceeding remaining
   Guarda can cross into HP as Breakthrough pressure.
7. An attack against an empty enemy field damages the opposing hero directly,
   except that direct damage is blocked during turn 1 before the bot responds.
8. After an action resolves, the player advances the turn; the bot summons and
   attacks under its active personality.
9. A side that reaches 0 HP loses. If both decks and hands are exhausted, the
   side with more HP wins.

## Match Phases

- `choose`: main phase; summon, cast, arm, evolve, fuse or declare an attack.
- `result`: a combat has resolved and the player may advance the turn.
- `finished`: a winner has been recorded; only replay/history or a new duel is
  available.

## Cards And Field

The catalog has 103 cards: 83 monsters, 10 spells and 10 traps. It includes
40 Common, 60 Uncommon and 3 Legendary cards.

Each public card includes identity, type, rarity, family, tier, cost, combat
stats, ability metadata and art. Monsters expose `attack`, `guard`,
`current_guard`, optional `evolution_id` and runtime field state.

## Evolution And Fusion

- **Evolution from hand:** two matching base monsters in hand can become their
  evolved form through `POST /api/rebirth/evolve`.
- **Field fusion:** two adjacent, living, matching monsters with an evolution
  target can merge on the battlefield through `POST /api/labs/fusion`. The
  materials are discarded and the resulting evolved creature enters the
  center-compatible slot with Breakthrough.

Both actions are authoritative commands, persist in signed-in match history
and are replayable from their command/event stream.

## Campaign And Progression

Campaign mode contains ten sequential encounters, from **Acolito da Brasa** to
**Rei Cinzento**. Boss nodes can alter HP, opening shields, draw and mana, and
award XP once a victory is persisted. Collection, deck editing, free-beta
boosters, market offers, wallet ledger, achievements and reward progression are
Rebirth-native product surfaces.

## Active Gameplay APIs

- `POST /api/rebirth/start`
- `GET /api/rebirth/campaign`
- `POST /api/rebirth/campaign/start`
- `POST /api/rebirth/play-card`
- `POST /api/rebirth/attack`
- `POST /api/rebirth/evolve`
- `POST /api/labs/fusion`
- `POST /api/rebirth/next-turn`

Successful responses use `{ "ok": true, "state": {}, "result": null }`.
Expected request failures use `{ "ok": false, "error": { "code": "...",
"message": "..." } }`.

Stable gameplay errors include `missing_match`, `invalid_phase`,
`missing_card`, `invalid_card`, `duplicate_not_available`,
`first_turn_direct_attack_blocked`, `invalid_fusion_material`,
`fusion_not_adjacent`, `match_finished` and `malformed_request`.
