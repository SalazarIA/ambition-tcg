# Ascension Duel Architecture

Ascension Duel is the canonical Ambitionz combat architecture for the main product route.

## Match State

Each match contains:

- `id`
- `version = ascension_duel_v1`
- `round`
- `phase`
- `player`
- `opponent`
- `chronicle`
- `winner`
- `seed`
- `created_at`

No main match state contains a three-slot board or lane array.

## Player State

Each side contains:

- `hp`
- `ambition`
- `deck`
- `hand`
- `echo`
- `active_champion`
- `bound_souls`
- `relic`
- `schemes`
- `intent`
- `status`
- `last_actions`
- `domination_marks`
- `ascended`

## Card Model

Canonical card types are:

- `champion`
- `technique`
- `relic`
- `scheme`
- `ascension`

Every card supports at least one clear purpose:

- Summon
- Bind
- Burn
- Equip
- Set
- Cast
- Ascend

Overrule and Dominate are Ambition Core actions layered above card play.

## Engine Boundary

`services/ascension_engine.py` is pure Python and deterministic under a seed. It does not import BE2 or lane logic. It owns match creation, draw, intent selection, card play, Mind Clash resolution, Ambition gain/spend, Domination checks and serialization.

## Public Contract

`services/ascension_payloads.py` exposes safe match state:

- active Champion
- Bound Souls
- Relic
- safe Scheme data
- Ambition
- HP
- Intent state
- hand for the current player
- Echo count
- Round
- phase
- winner
- Chronicle

Enemy hidden Schemes remain hidden until revealed.
