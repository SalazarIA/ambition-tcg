# Ambitionz Rebirth Rulebook

Ambitionz Rebirth is the active Ambitionz MVP architecture. It replaces the old Arena, BE2, Ascension, collection, deck builder, shop, missions, ranking, progression and economy loops in the running product.

## Core Loop

One card. One decision. One clash.

1. Both sides begin with 30 HP.
2. Both sides draw a hand of 5 monsters.
3. Each turn, the player chooses exactly 1 monster from hand.
4. The bot responds with exactly 1 monster from hand.
5. Higher attack wins the clash.
6. The winner deals damage to the loser.
7. Damage is based on attacker attack minus half of defender guard, with a minimum of 1.
8. A tie is a Clash: no damage is dealt.
9. First side to 0 HP loses the match.
10. After a resolved turn, both sides draw back up to 5 cards when possible.

## Card Model

Each monster has:

- `id`
- `name`
- `family`
- `role`
- `tier`
- `attack`
- `guard`
- `power` as attack-compatible UI shorthand
- `element`
- `evolution_id`
- `ability_name`
- `ability_text`
- `flavor`
- `art`

## Evolution

Evolution is available before playing a card.

If the player has 2 matching base monsters in hand and that monster has an `evolution_id`, the two copies can combine into the evolved monster. The consumed copies go to discard and the evolved monster enters the hand immediately.

Initial direct evolutions:

- Dreadclaw + Dreadclaw = Dreadmaw
- Stoneshell + Stoneshell = Stonewarden
- Skywarden + Skywarden = Stormwarden
- Ironbastion + Ironbastion = Ironbulwark
- Embermaw + Embermaw = Embermaw Alpha

## MVP Catalog

Base monsters:

- Dreadclaw, Fire, Beast, tier 1, attack 6, guard 6
- Stoneshell, Earth, Guardian, tier 1, attack 2, guard 5
- Shadewisp, Shadow, Assassin, tier 1, attack 3, guard 2
- Skywarden, Air, Avian, tier 1, attack 4, guard 3
- Ironbastion, Metal, Guardian, tier 1, attack 3, guard 6
- Embermaw, Fire, Wyrm, tier 1, attack 7, guard 6
- Voidstalker, Void, Hunter, tier 1, attack 5, guard 2
- Nightfang, Shadow, Beast, tier 1, attack 4, guard 2

Evolved monsters:

- Dreadmaw, Fire, Apex Beast, tier 2, attack 9, guard 7
- Stonewarden, Earth, Guardian, tier 2, attack 4, guard 8
- Stormwarden, Air, Avian, tier 2, attack 7, guard 5
- Ironbulwark, Metal, Guardian, tier 2, attack 5, guard 9
- Embermaw Alpha, Fire, Wyrm, tier 2, attack 10, guard 7

## API Contract

- `GET /health`
- `GET /`
- `GET /rebirth`
- `POST /api/rebirth/start`
- `POST /api/rebirth/play-card`
- `POST /api/rebirth/evolve`
- `POST /api/rebirth/next-turn`

The MVP uses JSON APIs only. Socket.io is not part of Ambitionz Rebirth MVP.
