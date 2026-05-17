import pytest

from services.ascension_cards import build_ascension_starter_deck, get_card_by_id
from services.ascension_engine import (
    AscensionActionError,
    attempt_dominate,
    choose_intent,
    create_match,
    draw_cards,
    legal_actions,
    play_card,
    resolve_clash,
    spend_ambition,
)


def deck_with(*ids):
    cards = [get_card_by_id(card_id) for card_id in ids]
    filler = build_ascension_starter_deck(seed="engine-filler")
    return cards + filler


def test_match_creation_starts_round_and_draws_hands():
    match = create_match(seed="engine-create")

    assert match["version"] == "ascension_duel_v1"
    assert match["round"] == 1
    assert match["phase"] == "intent"
    assert len(match["player"]["hand"]) == 5
    assert len(match["opponent"]["hand"]) == 5
    assert "lane" not in match


def test_draw_cards_moves_from_deck_to_hand():
    match = create_match(seed="engine-draw")
    before = len(match["player"]["hand"])

    draw_cards(match, "player", 2)

    assert len(match["player"]["hand"]) == before + 2


def test_champion_summon_and_replacement_moves_old_active_to_echo():
    match = create_match(
        seed="summon",
        player_deck=deck_with("ember_vowbound", "glass_tyrant", "ashen_pulse", "cinder_halo", "sunken_oath"),
    )

    play_card(match, "player", "ember_vowbound", mode="summon")
    play_card(match, "player", "glass_tyrant", mode="summon")

    assert match["player"]["active_champion"]["id"] == "glass_tyrant"
    assert any(card["id"] == "ember_vowbound" for card in match["player"]["echo"])


def test_champion_bind_and_bound_soul_limit():
    match = create_match(
        seed="bind",
        player_deck=deck_with(
            "ember_vowbound",
            "glass_tyrant",
            "crownless_warden",
            "hollow_orchard",
            "velvet_martyr",
        ),
    )

    play_card(match, "player", "ember_vowbound", mode="summon")
    play_card(match, "player", "glass_tyrant", mode="bind")
    play_card(match, "player", "crownless_warden", mode="bind")
    play_card(match, "player", "hollow_orchard", mode="bind")

    assert len(match["player"]["bound_souls"]) == 3
    with pytest.raises(AscensionActionError) as error:
        play_card(match, "player", "velvet_martyr", mode="bind")
    assert error.value.code == "bound_soul_limit"


def test_technique_burn_gives_ambition_and_moves_to_echo():
    match = create_match(seed="burn", player_deck=deck_with("ashen_pulse", "ember_vowbound", "cinder_halo", "sunken_oath", "iron_prayer"))

    play_card(match, "player", "ashen_pulse", mode="burn")

    assert match["player"]["ambition"] == 2
    assert any(card["id"] == "ashen_pulse" for card in match["player"]["echo"])


def test_relic_equip_replaces_old_relic_to_echo():
    match = create_match(seed="relic", player_deck=deck_with("cinder_halo", "obsidian_ledger", "ember_vowbound", "ashen_pulse", "sunken_oath"))

    play_card(match, "player", "cinder_halo", mode="equip")
    play_card(match, "player", "obsidian_ledger", mode="equip")

    assert match["player"]["relic"]["id"] == "obsidian_ledger"
    assert any(card["id"] == "cinder_halo" for card in match["player"]["echo"])


def test_scheme_set_and_intent_selection():
    match = create_match(seed="scheme", player_deck=deck_with("sunken_oath", "ember_vowbound", "ashen_pulse", "cinder_halo", "iron_prayer"))

    play_card(match, "player", "sunken_oath", mode="set")
    choose_intent(match, "player", "Scheme")

    assert match["player"]["schemes_count"] if "schemes_count" in match["player"] else len(match["player"]["schemes"]) == 1
    assert match["player"]["intent"] == "Scheme"


def test_clash_resolves_and_advances_round_without_deadlock():
    match = create_match(
        seed="clash",
        player_deck=deck_with("ember_vowbound", "ashen_pulse", "cinder_halo", "sunken_oath", "iron_prayer"),
        opponent_deck=deck_with("crownless_warden", "debt_of_the_starless", "saint_engine", "thorn_pact", "mirror_break"),
    )
    play_card(match, "player", "ember_vowbound", mode="summon")
    play_card(match, "opponent", "crownless_warden", mode="summon")
    choose_intent(match, "player", "Strike")
    choose_intent(match, "opponent", "Focus")

    resolve_clash(match)

    assert match["round"] == 2
    assert match["phase"] == "intent"
    assert any(event["type"] == "clash_resolved" for event in match["chronicle"])


def test_dominate_success_and_safe_unavailable_path():
    match = create_match(seed="dominate", player_deck=deck_with("ember_vowbound", "ashen_pulse", "cinder_halo", "sunken_oath", "iron_prayer"))

    unavailable = attempt_dominate(match, "player")
    assert unavailable["ok"] is False

    play_card(match, "player", "ember_vowbound", mode="summon")
    match["player"]["ambition"] = 20
    match["opponent"]["hp"] = 10
    result = attempt_dominate(match, "player")

    assert result["ok"] is True
    assert result["success"] is True
    assert match["winner"] == "player"


def test_legal_actions_and_spend_ambition_errors_are_structured():
    match = create_match(seed="legal")
    actions = legal_actions(match, "player")

    assert actions["intents"] == ["Strike", "Guard", "Focus", "Scheme"]
    with pytest.raises(AscensionActionError) as error:
        spend_ambition(match, "player", 99, reason="test")
    assert error.value.to_dict()["code"] == "not_enough_ambition"
