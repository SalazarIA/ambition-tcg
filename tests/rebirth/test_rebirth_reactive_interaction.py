"""Onda 3 do roadmap industrial: robustez da interação reativa (I7-I8).

O sistema reativo já existe (10 traps disparando na interrupt chain e spells que
miram unidade via _spell_effects_for_target). Esta suíte aplica a régua
industrial da Onda 1 — invariantes, replay e determinismo — a esses caminhos.
"""

import pytest

from services.rebirth_invariants import run_deterministic_command_fuzz


TRAP_DECK = [f"card_{number:03d}" for number in range(91, 101)]  # 10 traps reativas
DAMAGE_SPELLS = ["card_084", "card_090"]  # spells de dano que miram unidade


@pytest.mark.parametrize("seed", ["traps-0", "traps-1"])
def test_reactive_traps_in_combat_hold_invariants(seed):
    """I7: traps disparando em combate (interrupt chain) não corrompem estado nem replay."""
    player_deck = (TRAP_DECK * 2 + ["card_001", "card_041"] * 5)[:30]
    bot_deck = ["card_011", "card_016"] * 15  # FIRE agressivo: ataca e dispara as traps
    result = run_deterministic_command_fuzz(
        seed,
        max_commands=22,
        match_kwargs={"player_card_ids": player_deck, "bot_card_ids": bot_deck},
    )

    assert result.ok, [violation.code for violation in result.final_report.violations]
    assert result.replay and result.replay["ok"] is True


@pytest.mark.parametrize("seed", ["spell-target-0", "spell-target-1"])
def test_unit_targeted_spells_hold_invariants(seed):
    """I8: spells de dano mirando unidades inimigas mantêm invariantes e replay."""
    player_deck = (DAMAGE_SPELLS * 5 + ["card_001", "card_002"] * 5)[:30]
    bot_deck = ["card_041", "card_046"] * 15  # EARTH: corpos de Guarda alta para mirar
    result = run_deterministic_command_fuzz(
        seed,
        max_commands=22,
        match_kwargs={"player_card_ids": player_deck, "bot_card_ids": bot_deck},
    )

    assert result.ok, [violation.code for violation in result.final_report.violations]
    assert result.replay and result.replay["ok"] is True


def test_reactive_interaction_is_reproducible():
    """A interação reativa (traps + spells de alvo) é determinística por seed."""
    deck = (TRAP_DECK + DAMAGE_SPELLS + ["card_001"] * 8)[:30]
    kwargs = {"player_card_ids": deck, "bot_card_ids": ["card_011"] * 30}
    first = run_deterministic_command_fuzz("reactive-repro", max_commands=18, match_kwargs=kwargs)
    second = run_deterministic_command_fuzz("reactive-repro", max_commands=18, match_kwargs=kwargs)

    assert first.command_types == second.command_types
    assert first.final_report.canonical_hash == second.final_report.canonical_hash
