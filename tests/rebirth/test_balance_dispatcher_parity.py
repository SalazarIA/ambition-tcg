"""Item 3: the balance lab now drives matches through the real dispatcher.

Audit P1.3 flagged that the simulator called the engine directly, so balance
numbers could diverge from production (which goes through the command
dispatcher). These tests lock that the lab uses the dispatcher AND that doing
so does not change match outcomes.
"""
from services import rebirth_balance as rb
from services.rebirth_engine import play_card as engine_play_card, start_match


def _first_monster(match):
    energy = int(match["player"].get("energy") or match["player"].get("max_energy") or 1)
    return next(
        card for card in match["player"]["hand"]
        if card["type"] == "MONSTER" and int(card.get("cost", 1) or 1) <= energy
    )


def test_balance_play_card_routes_through_dispatcher():
    raw = start_match(seed="parity-seed")
    dispatched = start_match(seed="parity-seed")

    engine_play_card(raw, card_instance_id=_first_monster(raw)["instance_id"])
    rb.play_card(dispatched, card_instance_id=_first_monster(dispatched)["instance_id"])

    # The dispatcher leaves command-dispatch provenance the raw engine path lacks.
    assert "_command_dispatch_depth" in dispatched
    assert "_command_dispatch_depth" not in raw

    # …and the gameplay outcome is identical (no balance drift from routing).
    assert len(dispatched["player"]["battlefield"]) == len(raw["player"]["battlefield"]) == 1
    assert dispatched["player"]["battlefield"][0]["id"] == raw["player"]["battlefield"][0]["id"]


def test_balance_simulation_still_runs_and_reports():
    # Core report contract holds after the dispatcher switch.
    report = rb.simulate_balance(matches=12)
    assert report["winners"]
    assert report["card_stats"]
    assert report["profile_results"]
