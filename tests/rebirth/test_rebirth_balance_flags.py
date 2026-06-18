from services.rebirth_balance import balance_flags
from services.rebirth_cards import get_card


def _high_conditional_win_rate(card):
    return balance_flags(
        plays=40,
        match_uses=40,
        wins=34,
        damage=120,
        matches=100,
        dead_count=0,
        evolve_count=0,
        card=card,
    )


def test_direct_damage_finisher_downgrades_conditional_dominance_signal():
    assert _high_conditional_win_rate(get_card("card_001")) == ["dominant"]
    assert _high_conditional_win_rate(get_card("card_084")) == ["selection-biased-win-rate"]
