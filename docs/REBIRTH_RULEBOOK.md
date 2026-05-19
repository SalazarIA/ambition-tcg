# Ambitionz Rebirth Rulebook

Ambitionz Rebirth is the active Ambitionz MVP architecture. It replaces the old Arena, BE2, Ascension, collection, deck builder, shop, missions, ranking, progression and economy loops in the running product.

## Core Loop

One card. One decision. One clash.

1. Both sides begin with 3 HP.
2. Both sides draw a hand of 5 monsters.
3. Each turn, the player chooses exactly 1 monster from hand.
4. The bot responds with exactly 1 monster from its hand.
5. Higher power wins the turn.
6. The loser of the turn loses 1 HP.
7. A tie is a Clash: no HP is lost.
8. First side to 0 HP loses the match.
9. After a resolved turn, both sides draw back up to 5 cards when possible.

## Evolution

Evolution is available before playing a card.

If the player has 2 matching base monsters in hand and that monster has an `evolution_id`, the two copies can combine into the evolved monster. The consumed copies go to discard and the evolved monster enters the hand immediately.

Initial direct evolutions:

- Ember Cub + Ember Cub = Ember Fang
- Tide Imp + Tide Imp = Tide Brute
- Stone Pup + Stone Pup = Stone Golem
- Night Sprout + Night Sprout = Night Bloom

## MVP Catalog

Base monsters:

- Ember Cub, Fire, tier 1, power 2
- Tide Imp, Water, tier 1, power 2
- Stone Pup, Earth, tier 1, power 3
- Night Sprout, Shadow, tier 1, power 1
- Spark Hare, Volt, tier 1, power 4
- Glass Moth, Air, tier 1, power 3
- Iron Beetle, Metal, tier 1, power 5
- Mist Lynx, Water, tier 1, power 4
- Sun Ram, Light, tier 1, power 3
- Void Tadpole, Void, tier 1, power 2

Evolved monsters:

- Ember Fang, Fire, tier 2, power 5
- Tide Brute, Water, tier 2, power 5
- Stone Golem, Earth, tier 2, power 6
- Night Bloom, Shadow, tier 2, power 4

## API Contract

- `GET /health`
- `GET /`
- `GET /rebirth`
- `POST /api/rebirth/start`
- `POST /api/rebirth/play-card`
- `POST /api/rebirth/evolve`
- `POST /api/rebirth/next-turn`

The MVP uses JSON APIs only. Socket.io is not part of Ambitionz Rebirth MVP.
