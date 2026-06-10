from copy import deepcopy
from pathlib import Path
from time import perf_counter

import pytest

from services.rebirth_contracts import RebirthError
from services.rebirth_cards import create_card_instance
from services.rebirth_dispatcher import (
    CommandDispatcher,
    DeclareAttackCommand,
    EndTurnCommand,
    RebirthCommand,
    SummonCardCommand,
    dispatch_command,
)
from services.rebirth_domain import canonical_state_hash
from services.rebirth_engine import play_card, start_match
from services.rebirth_reducers import reduce_events


ROOT = Path(__file__).resolve().parents[2]


def assert_reducer_equivalence(seed, actions, *, bot_profile_id="defensive", setup=None):
    match = start_match(seed=seed, bot_profile_id=bot_profile_id)
    if setup:
        setup(match)
    base = deepcopy(match)
    start_index = len(match["events"])

    actions(match)

    reconstructed = reduce_events(base, match["events"][start_index:])
    assert canonical_state_hash(reconstructed) == canonical_state_hash(match)
    return match, reconstructed


def first_hand_instance(match, card_id=None):
    for card in match["player"]["hand"]:
        if card_id is None or card["id"] == card_id:
            return card["instance_id"]
    raise AssertionError(f"card not found in hand: {card_id}")


def seed_player_card(card_id, sequence=99):
    """Setup compatível com o shuffle real: injeta a carta na mão ANTES do
    snapshot base, então vale igualmente para o runtime e para o replay."""

    def _setup(match):
        match["player"]["hand"].insert(0, create_card_instance(card_id, "player", sequence))

    return _setup


def test_v64_spell_reconstructs_byte_equivalent_state():
    assert_reducer_equivalence(
        "v64-spell-equivalence",
        lambda match: dispatch_command(match, SummonCardCommand(card_instance_id=first_hand_instance(match))),
    )


def test_v64_monster_summon_reconstructs_byte_equivalent_state():
    assert_reducer_equivalence(
        "v64-summon-equivalence",
        lambda match: dispatch_command(match, SummonCardCommand(card_instance_id=first_hand_instance(match, "card_001"), field_slot=1)),
        setup=seed_player_card("card_001"),
    )


def test_v64_turn_rollover_draw_energy_ready_and_bot_summon_are_reconstructable():
    def actions(match):
        dispatch_command(match, SummonCardCommand(card_instance_id=first_hand_instance(match, "card_001"), field_slot=0))
        dispatch_command(match, EndTurnCommand(turn=match["turn"]))

    assert_reducer_equivalence("v64-turn-equivalence", actions, setup=seed_player_card("card_001"))


def test_v64_field_combat_damage_cleanup_reconstructs_byte_equivalent_state():
    def actions(match):
        dispatch_command(match, SummonCardCommand(card_instance_id=first_hand_instance(match, "card_001"), field_slot=0))
        dispatch_command(match, EndTurnCommand(turn=match["turn"]))
        dispatch_command(
            match,
            DeclareAttackCommand(
                attacker_instance_id=match["player"]["battlefield"][0]["instance_id"],
                target_instance_id=match["bot"]["battlefield"][0]["instance_id"],
            ),
        )

    assert_reducer_equivalence("v64-combat-equivalence", actions, setup=seed_player_card("card_001"))


def test_v64_trap_arm_reconstructs_byte_equivalent_state():
    assert_reducer_equivalence(
        "v64-trap-arm-equivalence",
        lambda match: dispatch_command(match, SummonCardCommand(card_instance_id=first_hand_instance(match, "card_091"))),
        setup=lambda match: match["player"]["hand"].insert(0, create_card_instance("card_091", "player", 99)),
    )


def test_v64_trap_interrupt_chain_reconstructs_byte_equivalent_state():
    """Traps agora têm contexto: a interrupção vem da trap do BOT quando o
    jogador ataca (a trap do atacante não pune o próprio ataque)."""

    def setup(match):
        match["player"]["hand"].insert(0, create_card_instance("card_001", "player", 99))
        match["bot"]["hand"].insert(0, create_card_instance("card_093", "bot", 98))

    def actions(match):
        dispatch_command(match, SummonCardCommand(card_instance_id=first_hand_instance(match, "card_001"), field_slot=0))
        dispatch_command(match, EndTurnCommand(turn=match["turn"]))
        assert match["bot"]["battlefield"], "bot precisa ter invocado no turno dele"
        dispatch_command(
            match,
            DeclareAttackCommand(
                attacker_instance_id=match["player"]["battlefield"][0]["instance_id"],
                target_instance_id=match["bot"]["battlefield"][0]["instance_id"],
            ),
        )

    match, _ = assert_reducer_equivalence("v64-trap-interrupt-equivalence", actions, setup=setup)
    assert any(
        (event.get("type") or event.get("event_type")) == "TRAP_TRIGGERED" and event.get("actor") == "bot"
        for event in match["events"]
    )


def test_v64_routes_use_command_dispatcher_instead_of_engine_calls():
    source = (ROOT / "app.py").read_text(encoding="utf-8")

    assert "from services.rebirth_engine import (\n    declare_attack" not in source
    assert "\n            play_card(" not in source
    assert "\n        declare_attack(" not in source
    assert "next_turn(match)" not in source
    assert "evolve_duplicate(" not in source
    assert "dispatch_command(" in source


def test_v64_strict_match_rejects_direct_engine_bypass():
    match = start_match(seed="v64-strict-bypass")
    match["_require_command_dispatcher"] = True

    with pytest.raises(RebirthError) as error:
        play_card(match, card_instance_id=first_hand_instance(match))

    assert error.value.code == "dispatcher_required"


def test_v64_strict_match_accepts_command_dispatcher_entrypoint():
    match = start_match(seed="v64-strict-dispatch")
    match["player"]["hand"].insert(0, create_card_instance("card_001", "player", 99))
    match["_require_command_dispatcher"] = True

    dispatch_command(match, SummonCardCommand(card_instance_id=first_hand_instance(match, "card_001"), field_slot=0))

    assert match["player"]["battlefield"][0]["id"] == "card_001"


def test_v64_invalid_dispatcher_command_raises_structured_error():
    class UnknownCommand(RebirthCommand):
        pass

    match = start_match(seed="v64-invalid-dispatch")

    with pytest.raises(RebirthError) as error:
        CommandDispatcher().dispatch(match, UnknownCommand())

    assert error.value.code == "unsupported_command"


def test_v64_http_invalid_command_payload_returns_400(client):
    state = client.post("/api/rebirth/start", json={"seed": "v64-http-dispatch"}).get_json()["state"]

    response = client.post("/api/rebirth/play-card", json={"match_id": state["match_id"]})
    payload = response.get_json()

    assert response.status_code == 400
    assert payload["ok"] is False
    assert payload["error"]["code"] == "missing_card"


def test_v64_state_clone_and_reducer_replay_500_rounds_stays_bounded():
    match = start_match(seed="v64-load")
    match["player"]["hand"].insert(0, create_card_instance("card_001", "player", 99))
    base = deepcopy(match)
    dispatch_command(match, SummonCardCommand(card_instance_id=first_hand_instance(match, "card_001"), field_slot=0))
    events = match["events"][len(base["events"]):]

    started = perf_counter()
    for _ in range(500):
        reconstructed = reduce_events(base, events)
        assert reconstructed["player"]["battlefield"][0]["id"] == "card_001"
    elapsed = perf_counter() - started

    assert elapsed < 30.0
