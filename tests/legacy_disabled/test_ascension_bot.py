from services.ascension_bot import bot_profile_payload, choose_bot_card_action, choose_bot_intent, run_bot_turn
from services.ascension_cards import get_card_by_id
from services.ascension_engine import choose_intent, create_match, play_card, resolve_clash


def _play_simple_player_action(match):
    player = match["player"]
    if not player.get("active_champion"):
        champion = next((card for card in player["hand"] if card["type"] == "champion"), None)
        if champion:
            play_card(match, "player", champion["id"], mode="summon")
            return
    technique = next((card for card in player["hand"] if card["type"] == "technique"), None)
    if technique:
        play_card(match, "player", technique["id"], mode="cast")
        return
    if player["hand"]:
        play_card(match, "player", player["hand"][0]["id"], mode="burn")


def test_bot_can_play_ten_rounds_without_deadlock():
    match = create_match(seed="bot-deadlock")

    for index in range(10):
        if match.get("winner"):
            break
        choose_intent(match, "player", "Focus" if index % 3 == 0 else "Strike")
        _play_simple_player_action(match)
        run_bot_turn(match)
        resolve_clash(match)

    assert match["phase"] in {"intent", "finished"}
    assert match["round"] >= 2
    assert any(event["side"] == "opponent" for event in match["chronicle"])


def test_bot_summons_champion_if_missing():
    match = create_match(
        seed="bot-summon",
        opponent_deck=[
            get_card_by_id("crownless_warden"),
            get_card_by_id("debt_of_the_starless"),
            get_card_by_id("saint_engine"),
            get_card_by_id("thorn_pact"),
            get_card_by_id("mirror_break"),
        ],
    )

    run_bot_turn(match)

    assert match["opponent"]["active_champion"]["id"] == "crownless_warden"


def test_bot_profiles_influence_intent_and_actions():
    aggressive = create_match(seed="profile-aggressive", bot_profile="Aggressor")
    ascender = create_match(seed="profile-ascender", bot_profile="Ascender")

    assert choose_bot_intent(aggressive, profile="Aggressor") == "Strike"
    assert choose_bot_intent(ascender, profile="Ascender") == "Focus"
    assert bot_profile_payload("Defensive")["label"] == "Defensive"

    action = choose_bot_card_action(aggressive, profile="Aggressor")
    assert action is not None
