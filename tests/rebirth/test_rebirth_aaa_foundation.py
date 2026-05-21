import asyncio
import inspect

import pytest

from services.rebirth_engine import EffectStack, RebirthError, play_card, start_match
from services.rebirth_persistence import (
    Base,
    RebirthPersistenceError,
    active_market_offers,
    buy_market_offer,
    configure_async_database,
    create_market_offer,
    load_match_state,
    log_transaction,
    save_match_state,
)
from services.rebirth_state import TurnPhase, set_turn_phase


def test_effect_stack_applies_lifo_status_effects():
    match = start_match(seed="effect-stack")
    stack = EffectStack()

    stack.push_effect({"type": "status", "side": "bot", "status": "burn", "potency": 2, "turns": 2})
    stack.push_effect({"type": "shield", "side": "player", "amount": 3, "turns": 1})

    events = stack.resolve_stack(match)

    assert "gains a 3-point shield" in events[0]
    assert "affected by burn" in events[1]
    assert match["player"]["statuses"]["shield"]["potency"] == 3
    assert match["bot"]["statuses"]["burn"]["potency"] == 2

    tick_stack = EffectStack()
    tick_stack.push_effect({"type": "status_tick", "side": "bot"})
    tick_events = tick_stack.resolve_stack(match)

    assert match["bot"]["hp"] == 28
    assert "burn damage" in tick_events[0]


def test_turn_phase_blocks_card_play_outside_main_phase():
    match = start_match(seed="turn-phase-guard")
    set_turn_phase(match, TurnPhase.DRAW_PHASE)
    card = match["player"]["hand"][0]

    with pytest.raises(RebirthError) as error:
        play_card(match, card_instance_id=card["instance_id"])

    assert error.value.code == "invalid_phase"


def test_async_postgres_persistence_contract_is_declared(monkeypatch):
    monkeypatch.delenv("REBIRTH_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_URL", raising=False)
    configure_async_database("")

    assert {"user_accounts", "user_collections", "game_sessions", "economy_transactions", "market_offers"}.issubset(
        set(Base.metadata.tables)
    )
    assert inspect.iscoroutinefunction(save_match_state)
    assert inspect.iscoroutinefunction(load_match_state)
    assert inspect.iscoroutinefunction(log_transaction)
    assert inspect.iscoroutinefunction(create_market_offer)
    assert inspect.iscoroutinefunction(buy_market_offer)
    assert inspect.iscoroutinefunction(active_market_offers)

    with pytest.raises(RebirthPersistenceError) as error:
        asyncio.run(save_match_state("rebirth-test", {"turn": 1, "phase": "choose"}))

    assert error.value.code == "database_not_configured"
