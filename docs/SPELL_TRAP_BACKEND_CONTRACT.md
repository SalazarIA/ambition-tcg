# Spell/Trap Backend Contract V1

This contract formalizes the card-play payload used by Arena Clean v48, `arena_command_v1`, legacy `az48_*` events and BE2. It is additive: old payloads with only `card_id` plus `lane` or `target` remain valid.

## Accepted Fields

- `card_id`: canonical catalog id or hand card id.
- `card_instance_id`: optional client/backend instance id.
- `card_type`: `creature`, `monster`, `spell`, `trap` or fallback `card`.
- `official_type`: optional catalog type such as `Monster`, `Spell` or `Trap`.
- `lane`: player lane for creature summons.
- `target`: legacy target token, still accepted.
- `target_type`: `hero`, `creature`, `lane`, `self` or `none`.
- `target_owner`: `player`, `opponent`, `enemy`, `bot` or `self`.
- `target_lane`: `left`, `center` or `right`.
- `target_id`: optional richer target identifier.
- `cast_mode`: `summon`, `cast`, `prepare`, `instant` or `targeted`.
- `prepared`: boolean hint for Trap preparation.
- `client_selected_target`: optional visual target token used by the frontend.
- `source`: optional client/source label for diagnostics.

Unknown fields are ignored. Missing fields fall back to legacy behavior.

## Normalization

BE2 normalizes:

- `monster` and `unit` into creature summons.
- `spell` and `magic` into spell resolution.
- `trap` into prepared trap state.
- visual target tokens such as `enemy_left` into `target_type=creature`, `target_owner=opponent`, `target_lane=left`.
- legacy `enemy_hero`, `self` and `lane:left` targets into the new target contract.

## Creature

Creatures require a valid player lane. If only legacy `lane` is supplied, the backend treats the card as a summon. Invalid or full lanes return a safe error and do not mutate the board.

## Spell

Spells are never summoned as lane creatures. BE2 infers a minimum effect from official effect metadata, name and text:

- damage/burn/weaken effects hit an enemy creature or enemy hero.
- heal effects recover the player or an allied creature.
- shield effects protect the player or an allied creature.
- draw/boost/focus/ambition effects grant Ambition when safe.
- unknown spell effects emit `spell_noop` rather than breaking the match.

## Trap

Traps are prepared into `prepared_traps` and `field.traps`. They are not lane creatures. During combat, prepared traps can trigger on incoming attacks:

- counter/thorn/ambush traps damage the attacker.
- shield/barrier/guard traps add shield before damage lands.
- snare/root/weaken traps reduce incoming damage.
- unknown traps remain safe and emit a no-op event if triggered.

Triggered traps are consumed and moved to discard.

## Combat Log Events

The backend emits structured events for UI timeline and round summaries:

- `spell_cast`
- `spell_targeted`
- `spell_damage`
- `spell_heal`
- `spell_shield`
- `spell_ambition`
- `spell_noop`
- `trap_prepared`
- `trap_triggered`
- `trap_noop`

Legacy events such as `card_played`, `shield_gain`, `hero_damage`, `creature_damage`, `round_end` and `match_finished` remain present where applicable.

## Compatibility Boundary

The frontend may send rich target data, but the backend always keeps a compatible legacy target. If a target is invalid or absent, BE2 picks the safest fallback for the inferred effect: enemy hero for damage, self for shield/heal/Ambition, or no-op for unclear effects.

