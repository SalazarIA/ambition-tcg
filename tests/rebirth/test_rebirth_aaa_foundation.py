import asyncio
from pathlib import Path

import pytest

import app as ambition_app
from services.rebirth_engine import EffectStack, RebirthError, play_card, start_match
from services.rebirth_bot import bot_decision_payload, choose_response, choose_response_async, resolve_bot_decision_payload
from services.rebirth_persistence import (
    RebirthPersistenceError,
    _is_serialization_failure,
)
from services.rebirth_schema import REQUIRED_TABLES, SCHEMA_VERSION
from services.rebirth_state import TurnPhase, set_turn_phase


def test_effect_stack_applies_lifo_status_effects():
    match = start_match(seed="effect-stack")
    stack = EffectStack()

    stack.push_effect({"type": "status", "side": "bot", "status": "burn", "potency": 2, "turns": 2})
    stack.push_effect({"type": "shield", "side": "player", "amount": 3, "turns": 1})

    events = stack.resolve_stack(match)

    assert "escudo de 3 pontos" in events[0]
    assert "afetado por queimadura" in events[1]
    assert match["player"]["statuses"]["shield"]["potency"] == 3
    assert match["bot"]["statuses"]["burn"]["potency"] == 2

    tick_stack = EffectStack()
    tick_stack.push_effect({"type": "status_tick", "side": "bot"})
    tick_events = tick_stack.resolve_stack(match)

    assert match["bot"]["hp"] == 28
    assert "dano de queimadura" in tick_events[0]


def test_turn_phase_blocks_card_play_outside_main_phase():
    match = start_match(seed="turn-phase-guard")
    set_turn_phase(match, TurnPhase.DRAW_PHASE)
    card = match["player"]["hand"][0]

    with pytest.raises(RebirthError) as error:
        play_card(match, card_instance_id=card["instance_id"])

    assert error.value.code == "invalid_phase"


def test_postgres_single_source_contract_is_declared(flask_app):
    assert {"users", "user_sessions", "user_collection", "economy_transactions", "market_offers", "wallet_ledger"}.issubset(REQUIRED_TABLES)
    assert SCHEMA_VERSION >= 2
    assert not hasattr(ambition_app, "run_async")
    assert not hasattr(ambition_app, "async_database_url")
    persistence_source = (Path(__file__).resolve().parents[2] / "services/rebirth_persistence.py").read_text(encoding="utf-8")
    assert "create_async_engine" not in persistence_source
    assert "AsyncSession" not in persistence_source
    assert "async def " not in persistence_source

    flask_app.config.update(TESTING=False, REBIRTH_ALLOW_SQLITE_TESTING=False, REBIRTH_DATABASE_URL=None)
    with pytest.raises(RebirthPersistenceError) as error:
        ambition_app.rebirth_repo()
    assert error.value.code == "database_not_configured"

    flask_app.config.update(TESTING=True)


def test_market_serialization_detector_only_retries_postgres_write_conflicts():
    class DatabaseFailure(Exception):
        def __init__(self, sqlstate):
            super().__init__(sqlstate)
            self.sqlstate = sqlstate

    class WrappedFailure(Exception):
        def __init__(self, original):
            super().__init__("wrapped database error")
            self.orig = original

    assert _is_serialization_failure(WrappedFailure(DatabaseFailure("40001")))
    assert not _is_serialization_failure(WrappedFailure(DatabaseFailure("23505")))


def test_bot_decision_is_available_as_isolated_async_payload():
    match = start_match(seed="bot-payload")
    player_card = match["player"]["hand"][0]
    payload = bot_decision_payload(
        match["bot"]["hand"],
        player_card,
        "opportunist",
        turn=match["turn"],
        match_id=match["match_id"],
    )
    sync_choice = choose_response(match["bot"]["hand"], player_card, "opportunist", turn=match["turn"], match_id=match["match_id"])
    projected = resolve_bot_decision_payload(payload)
    async_projected = asyncio.run(choose_response_async(payload))

    assert projected["decision"]["id"] == sync_choice["id"]
    assert async_projected["decision_instance_id"] == projected["decision_instance_id"]
    assert payload["context"]["match_id"] == match["match_id"]
