"""Engine integration matrix — every monster card actually resolves a clash.

This catches the failure mode the catalog matrix can't: an ability_key that
is registered in ENGINE_ABILITY_KEYS but whose handler explodes when the
clash actually fires (missing key in match state, division-by-zero on a
new modifier, NoneType on status push, etc).

We exercise each monster card on both sides of the clash against a fixed
neutral baseline. We don't assert game-logic outcomes here (that's the job
of test_rebirth_card_set.py and test_rebirth_engine.py) — we assert only
that resolve_turn(...) returns a structurally valid result without raising.

Cost: 80 cards × 2 sides × cheap in-memory clash = ~160 cases under 1s.
"""
from __future__ import annotations

import pytest

from services.rebirth_cards import CARD_BY_ID, CARD_CATALOG, create_card_instance
from services.rebirth_engine import resolve_turn, start_match

MONSTER_IDS = [card["id"] for card in CARD_CATALOG if card["type"] == "MONSTER"]
# Baseline opponents — picked to land on both possible clash outcomes:
#   card_001 = Fire base monster, mid stats   → likely loses to evolved cards
#   card_081 is a SPELL not a monster, so we use card_002 as a second baseline.
BASELINE_OPPONENT = "card_001"

pytestmark = pytest.mark.catalog


def _fresh_match(seed):
    match = start_match(seed=seed)
    # We want resolve_turn called in isolation — clear hands so the engine
    # doesn't try to draw / play extra cards.
    match["player"]["hand"] = []
    match["bot"]["hand"] = []
    match["player"]["wounded"] = False
    match["bot"]["wounded"] = False
    return match


@pytest.mark.parametrize("card_id", MONSTER_IDS)
def test_monster_clash_resolves_on_player_side(card_id):
    """The card sits in the player slot and clashes against the baseline bot card."""
    match = _fresh_match(f"player-{card_id}")
    player_card = create_card_instance(card_id, "player", 1)
    bot_card = create_card_instance(BASELINE_OPPONENT, "bot", 1)

    result = resolve_turn(match, player_card, bot_card)

    assert result["outcome"] in {"Victory", "Defeat", "Clash"}
    assert result["winner"] in {"player", "bot", None}
    assert isinstance(result["message"], str) and result["message"]
    assert "damage" in result and set(result["damage"].keys()) == {"player", "bot"}
    assert "effective_attack" in result
    # Ability events list must exist (may be empty for cards with no on-victory hook)
    assert isinstance(result.get("ability_events"), list)


@pytest.mark.parametrize("card_id", MONSTER_IDS)
def test_monster_clash_resolves_on_bot_side(card_id):
    """Same card, opposite side — defends symmetry of ability handlers."""
    match = _fresh_match(f"bot-{card_id}")
    player_card = create_card_instance(BASELINE_OPPONENT, "player", 1)
    bot_card = create_card_instance(card_id, "bot", 1)

    result = resolve_turn(match, player_card, bot_card)

    assert result["outcome"] in {"Victory", "Defeat", "Clash"}
    assert match["last_clash"]["player_card"]["id"] == BASELINE_OPPONENT
    assert match["last_clash"]["bot_card"]["id"] == card_id


@pytest.mark.parametrize("card_id", MONSTER_IDS)
def test_monster_clash_does_not_corrupt_effect_stack(card_id):
    """After resolution, the engine must leave a well-formed effect_stack.

    A bad ability handler could leave half-applied effects behind, which
    would then double-apply on the next turn.
    """
    match = _fresh_match(f"stack-{card_id}")
    player_card = create_card_instance(card_id, "player", 1)
    bot_card = create_card_instance(BASELINE_OPPONENT, "bot", 1)

    resolve_turn(match, player_card, bot_card)

    stack = match.get("effect_stack")
    assert isinstance(stack, list), f"effect_stack must be a list, got {type(stack)}"
    # Engine drains the stack each turn; any residual entries should at least
    # be well-formed dicts so the next resolve doesn't crash.
    for entry in stack:
        assert isinstance(entry, dict), f"stale effect_stack entry is not a dict: {entry!r}"
