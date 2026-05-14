# Battle Engine V2 Rulebook Snapshot

This document describes the current canonical BE2 combat contract used by
Arena Clean (`ambitionz_arena_clean_v50`). It documents behavior that exists
today; reward persistence, XP, missions and match history are resolved after
the match by Flask services, not inside the battle engine.

## Round Phases

1. A match starts in `created`.
2. `start_round` advances to `choose_action`.
3. Each side chooses one intent: `Strike`, `Guard` or `Focus`.
4. Each side may play one card if it has enough energy.
5. Each side marks ready.
6. Combat resolves lane by lane from `left` to `center` to `right`.
7. If nobody wins, the next round starts immediately.

## Energy

Players start with 2 energy. At the start of each round, max energy becomes
`min(10, 2 + round - 1)` and current energy refills to that max. Playing a
card spends its cost. A player can play at most one card per round.

## Draw

Each side starts with 5 cards. Round 1 preserves the opening hand. Later rounds
draw 1 card. If a deck is empty, the discard pile is reshuffled with the
match-controlled RNG, then drawing continues if possible.

## Intents

- `Strike`: offensive pressure. Creatures gain +2 attack this round, and
  Pressure Move gains +1 damage.
- `Guard`: defense and mitigation. The player gains 5 shield during combat,
  guarded creatures take 1 less combat damage, and instant shield cards gain
  +2 shield. Guard creatures attack with -1 attack this round.
- `Focus`: scaling. The player gains 3 Ambition at combat end, and instant
  effects gain +1 Ambition.

`Guard` and `Strike` also grant 1 Ambition at combat end.

## Cards

Creature cards enter one empty lane and grant their printed Ambition when
played. Support cards occupy the support slot and replace the previous support
if one exists. Spell and guard cards resolve immediately through the canonical
card effect resolver.

## Starter Identity

The beta starter deck keeps the 30-card structure and uses element identity as
readability guidance rather than a separate rules system:

- Fire means pressure and damage.
- Water means focus, resources and light sustain.
- Earth means defense and durable bodies.
- Plant means control and steady growth.

Card payloads expose element, faction, role, preview and effect summary so the
Arena can teach this identity without changing core combat rules.

## Lanes And Targeting

There are three lanes: `left`, `center` and `right`. Creature cards require an
empty lane. Instant cards may target `enemy_hero`, `self` or `lane:<lane>`.
Lane-targeted damage hits the enemy creature in that lane when present;
otherwise damage falls back to the enemy hero. Guard cards always grant shield
to their owner, even when their damage component targets the enemy hero.

## Shield And Damage

Shield absorbs hero damage before HP is reduced. Creature damage reduces
`current_hp` directly. Creature combat is simultaneous when both sides have a
creature in the same lane. Direct lane attacks hit the opposing hero when the
opposing lane is empty.

## Ambition

Ambition is gained from played cards, support bonuses, intent resolution and
some instant effects. At 10 Ambition, a side may arm Unleash before ready.
Unleash spends 10 Ambition, deals 10 hero damage during combat and grants 3
shield to the side that used it.

## Creature Death

After lane combat or lane-targeted spell damage, any creature with 0 or less
HP is moved to its owner's discard pile and the lane becomes empty. Deaths are
reported as structured `creature_death` events.

## End Of Match

The match ends when one hero reaches 0 HP. If both heroes fall together, or if
the max-round tiebreak triggers, the winner is decided by HP, then Ambition,
then last damage dealt, then draw.

## Reward And Post-Match Boundary

BE2 emits combat state, winner, reason, round summaries and structured combat
events. Persistent XP, missions, daily rewards, match history and
`post_match_summary` are awarded by the Flask layer after the match finishes.
