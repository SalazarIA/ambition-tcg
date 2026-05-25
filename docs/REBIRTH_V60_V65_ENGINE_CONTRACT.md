# Rebirth v60-v65 Engine Contract

This block hardens Rebirth around deterministic, server-authored gameplay.
It does not change the current Flask transport. The goal is to make the
engine replayable before realtime PvP becomes a product dependency.

## v60 - Domain Versioning

- `ENGINE_VERSION` is `rebirth_engine_v65`.
- `CARD_SET_VERSION` is `rebirth_card_set_v60`.
- Matches store `game_seed` separately from display seed and transport ids.
- Public payloads expose both `state_hash` and `canonical_state_hash`.

## v61 - Accepted Command Discipline

Commands now represent accepted player intent. Invalid card plays, invalid
slots and insufficient energy are rejected before `append_command` advances
the match version. Rejected input remains an API error, not a partial engine
mutation.

## v62 - Structured Effect Events

Stack effects still provide human-readable ability text for the current UI,
but each resolved effect also emits an `EFFECT_RESOLVED` event with structured
data:

- `effect_type`
- `side`
- `payload`
- optional `message`

This gives replay, telemetry and future clients a data contract that is not
tied to localized text.

## v63 - Deterministic Replay Harness

`services/rebirth_replay.py` can build a replay envelope from a live match and
re-run accepted commands from the initial seed/loadout/profile:

- `build_replay_envelope(match)`
- `replay_match(envelope_or_match)`
- `verify_replay(envelope_or_match)`

Replay verification compares canonical hashes, not presentation logs.

## v64 - Compressed Canonical Snapshots

Snapshots now include:

- `format_version`
- `canonical_state_hash`
- `state_encoding`
- compressed canonical state payload

The encoding is `gzip+base64+json`.

## v65 - Observability Hooks

Commands and events include:

- `engine_version`
- `card_set_version`
- `correlation_id`

These fields are deliberately simple so logs, support exports and future
metrics can join an action to its match/version without depending on a web
framework.

## Non-Goals

- No FastAPI migration in this block.
- No PvP transport in this block.
- No external card DSL in this block.

Those become lower-risk once the domain and replay contracts stay stable.
