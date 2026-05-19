# Rebirth Gameplay Core

Ambitionz Rebirth starts from one rule: each player controls only one active card.

## Player State

Each side has:

- `hp`
- `ambition`
- `deck`
- `hand`
- `discard`
- `active_card`
- `selected_intent`

## Match State

Each match has:

- `match_id`
- `round`
- `phase`
- `player`
- `opponent`
- `combat_log`
- `cinematic_event`
- `winner`
- `is_finished`

## Phases

The canonical phase names are:

- `START`
- `DRAW`
- `INTENT`
- `ACTION`
- `RESOLVE`
- `CLEANUP`

The first implementation starts with a four-card opening hand, then moves into Intent and Action decisions.

## Intents

- `STRIKE`: adds 2 attack for the Round.
- `GUARD`: reduces incoming damage by 3 for the Round.
- `FOCUS`: grants 2 Ambition before damage and adds 1 pressure once Ambition reaches 6.

Ambition is the future ultimate resource. In this block, it exists as a real state value and UI contract so later ultimate/ascension rules can be added safely.

## Active Card Rule

If a side has no `active_card`, it may activate a card from hand. If a side already has an `active_card`, playing another card replaces the current active card and moves the previous card to discard.

## Damage

Base damage is the active card's `attack`, with a minimum of 1. If a side has no active card, its base damage is 1. STRIKE adds 2. GUARD reduces received damage by 3. Starter damage is capped at 10 and cannot be negative.

## Combat Log Events

The alpha engine emits structured entries for `round_start`, `draw`, `intent_selected`, `card_activated`, `active_card_replaced`, `attack_calculated`, `guard_applied`, `ambition_gained`, `damage_dealt`, `round_resolved`, `round_end` and `match_finished`.

## Win Condition

Reduce the enemy HP to 0. When HP reaches 0 or lower, `winner` and `is_finished` are set.
