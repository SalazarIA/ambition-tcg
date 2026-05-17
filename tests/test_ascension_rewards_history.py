from services.ascension_cards import get_card_by_id
from services.ascension_engine import attempt_dominate, create_match, play_card
from services.ascension_history import append_history_record, build_history_record, read_history_records
from services.ascension_progression import build_ascension_rewards


def test_ascension_rewards_include_required_fields():
    match = create_match(
        seed="reward",
        player_deck=[
            get_card_by_id("ember_vowbound"),
            get_card_by_id("ashen_pulse"),
            get_card_by_id("cinder_halo"),
            get_card_by_id("sunken_oath"),
            get_card_by_id("iron_prayer"),
        ],
    )
    play_card(match, "player", "ember_vowbound", mode="summon")
    match["player"]["ambition"] = 20
    match["opponent"]["hp"] = 10
    attempt_dominate(match, "player")

    rewards = build_ascension_rewards(match)

    assert rewards["xp"] > 0
    assert rewards["gold"] > 0
    assert rewards["champion_progress"]["champion"] == "Ember Vowbound"
    assert rewards["unlock_progress"]["target"] == "First Ascension Cache"
    assert "Victory" in rewards["summary"] or "Win" in rewards["summary"]


def test_ascension_history_jsonl_round_trip(tmp_path):
    match = create_match(seed="history")
    rewards = build_ascension_rewards(match)
    record = build_history_record(match, reward=rewards)

    append_history_record(tmp_path, record)
    records = read_history_records(tmp_path)

    assert records[0]["match_id"] == match["id"]
    assert "result" in records[0]
    assert "rounds" in records[0]
    assert "champion" in records[0]
    assert "reward" in records[0]


def test_ascension_history_route_renders(client):
    response = client.get("/ascension-history")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Ascension Chronicle" in body
    assert "Duel Altar" in body or "Chronicle" in body
