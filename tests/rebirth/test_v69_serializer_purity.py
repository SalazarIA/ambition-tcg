"""v69: garantias canônicas após remoção do deepcopy desnecessário em _stable_value."""

from copy import deepcopy

from services.rebirth_dispatcher import EndTurnCommand, SummonCardCommand, dispatch_command
from services.rebirth_domain import canonical_card, canonical_state, canonical_state_hash
from services.rebirth_engine import start_match


def _match_with_history(seed: str):
    match = start_match(seed=seed, bot_profile_id="defensive")
    for _ in range(6):
        try:
            dispatch_command(
                match,
                SummonCardCommand(
                    card_instance_id=match["player"]["hand"][0]["instance_id"],
                    field_slot=0,
                ),
            )
        except Exception:
            pass
        try:
            dispatch_command(match, EndTurnCommand(turn=match["turn"]))
        except Exception:
            pass
    return match


def test_v69_canonical_card_does_not_mutate_input():
    match = _match_with_history("v69-purity-card")
    sample = next(
        card
        for side in ("player", "bot")
        for card in match[side].get("deck", [])
        if isinstance(card, dict)
    )
    snapshot = deepcopy(sample)
    canonical_card(sample)
    assert sample == snapshot, "canonical_card não pode mutar o card de origem"


def test_v69_canonical_state_byte_stable_across_clones():
    match = _match_with_history("v69-purity-state")
    clone = deepcopy(match)
    assert canonical_state(match) == canonical_state(clone)
    assert canonical_state_hash(match) == canonical_state_hash(clone)


def test_v69_canonical_state_shares_primitive_strings_safely():
    # Stable string identities OK; o teste só garante que canonical_state
    # não foi nivelado pra retornar referências do dict original (que poderiam
    # vazar mutações). Mutar o output canônico não deve refletir no match.
    match = _match_with_history("v69-purity-isolation")
    cs = canonical_state(match)
    player_deck_before = list(match["player"].get("deck", []))
    cs["player"]["deck"].clear()
    assert list(match["player"].get("deck", [])) == player_deck_before, (
        "canonical_state output não pode compartilhar referência das listas internas do match"
    )
