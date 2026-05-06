import os
import sys
import tempfile
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ["DATABASE_URL"] = os.environ.get(
    "ARENA_PLAYTEST_DATABASE_URL",
    f"sqlite:///{Path(tempfile.gettempdir()) / ('ambition_arena_playtest_' + uuid.uuid4().hex + '.db')}",
)
os.environ.setdefault("SECRET_KEY", "arena-playtest-secret-key")
os.environ.setdefault("WTF_CSRF_ENABLED", "true")
os.environ.setdefault("BETA_AUTO_VERIFY", "true")
os.environ.setdefault("MATCHMAKING_BOT_FALLBACK_SECONDS", "0.05")
os.environ.setdefault("ENVIRONMENT", "testing")

from app import active_matches, app, db, private_waiting_rooms, player_rooms, socket_state, socketio  # noqa: E402
from game.cards import CARD_CATALOG  # noqa: E402
from models import MatchHistory, User  # noqa: E402


class PlaytestFailure(AssertionError):
    pass


def reset_runtime():
    active_matches.clear()
    player_rooms.clear()
    private_waiting_rooms.clear()
    socket_state["waiting_player"] = None
    socket_state["waiting_since"] = None
    socket_state["waiting_deck_json"] = None
    socket_state["queue_generation"] = 0
    socket_state.setdefault("online_players", {}).clear()


def create_user(label):
    with app.app_context():
        user = User(username=f"{label}_{uuid.uuid4().hex[:8]}", email=f"{label}_{uuid.uuid4().hex[:8]}@example.com")
        user.set_password("StrongPass1")
        db.session.add(user)
        db.session.commit()
        return user.id, user.username


def socket_for(user_id):
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["_csrf_token"] = f"arena-playtest-{user_id}"
    socket_client = socketio.test_client(app, flask_test_client=client)
    socket_client.get_received()
    return client, socket_client


def disconnect(*socket_clients):
    for socket_client in socket_clients:
        try:
            if socket_client and socket_client.is_connected():
                socket_client.disconnect()
        except Exception:
            pass


def events(socket_client):
    return socket_client.get_received()


def event_names(received):
    return {packet["name"] for packet in received}


def latest_state(received):
    states = [packet["args"][0] for packet in received if packet["name"] == "game_state_update"]
    return states[-1] if states else None


def active_room():
    if not active_matches:
        raise PlaytestFailure("Expected an active match.")
    return next(iter(active_matches.keys()))


def first_monster():
    return next(card.copy() for card in CARD_CATALOG if card.get("type") == "Monster")


def assert_started(socket_client):
    received = events(socket_client)
    if "match_found" not in event_names(received):
        raise PlaytestFailure("Expected match_found event.")
    if not latest_state(received):
        raise PlaytestFailure("Expected game_state_update event.")
    return received


def start_training(difficulty):
    user_id, _username = create_user(f"training_{difficulty}")
    _client, socket_client = socket_for(user_id)
    socket_client.emit("join_training", {"difficulty": difficulty})
    received = assert_started(socket_client)
    room_id = active_room()
    if active_matches[room_id].get("bot_difficulty") != difficulty:
        raise PlaytestFailure(f"Expected {difficulty} bot difficulty.")
    disconnect(socket_client)
    return received


def start_bot_button():
    user_id, _username = create_user("botbutton")
    _client, socket_client = socket_for(user_id)
    socket_client.emit("join_bot_match")
    received = assert_started(socket_client)
    if not active_matches[active_room()].get("is_bot_match"):
        raise PlaytestFailure("Expected bot match.")
    disconnect(socket_client)


def pvp_queue_pairs_players():
    one_id, one_name = create_user("pvpone")
    two_id, two_name = create_user("pvptwo")
    _c1, s1 = socket_for(one_id)
    _c2, s2 = socket_for(two_id)
    s1.emit("join_queue")
    if socket_state.get("waiting_player", {}).get("name") != one_name:
        raise PlaytestFailure("First player did not enter queue.")
    s2.emit("join_queue")
    socketio.sleep(0.02)
    if "match_found" not in event_names(events(s1)) | event_names(events(s2)):
        raise PlaytestFailure("PvP pair did not receive match_found.")
    match = active_matches[active_room()]
    if {match["p1"]["name"], match["p2"]["name"]} != {one_name, two_name}:
        raise PlaytestFailure("PvP players do not match expected users.")
    disconnect(s1, s2)


def queue_falls_back_to_bot():
    user_id, _username = create_user("fallback")
    _client, socket_client = socket_for(user_id)
    app.config["MATCHMAKING_BOT_FALLBACK_SECONDS"] = 0.03
    socket_client.emit("join_queue")
    socketio.sleep(0.08)
    received = events(socket_client)
    if "match_found" not in event_names(received):
        raise PlaytestFailure("Fallback did not start a match.")
    match = active_matches[active_room()]
    if not match.get("matchmaking_fallback") or not match["p2"].get("is_bot"):
        raise PlaytestFailure("Expected matchmaking fallback bot match.")
    disconnect(socket_client)


def cancel_queue():
    user_id, _username = create_user("cancel")
    _client, socket_client = socket_for(user_id)
    app.config["MATCHMAKING_BOT_FALLBACK_SECONDS"] = 0.08
    socket_client.emit("join_queue")
    socket_client.emit("cancel_queue")
    socketio.sleep(0.12)
    if socket_state.get("waiting_player") or active_matches:
        raise PlaytestFailure("Queue cancellation left matchmaking state behind.")
    disconnect(socket_client)


def private_room_pairs_players():
    one_id, _one_name = create_user("privateone")
    two_id, _two_name = create_user("privatetwo")
    _c1, s1 = socket_for(one_id)
    _c2, s2 = socket_for(two_id)
    s1.emit("join_private_room", {"code": "ABCDE"})
    if "ABCDE" not in private_waiting_rooms:
        raise PlaytestFailure("Private room was not created.")
    s2.emit("join_private_room", {"code": "ABCDE"})
    socketio.sleep(0.02)
    if private_waiting_rooms or not active_matches:
        raise PlaytestFailure("Private room did not convert into active match.")
    disconnect(s1, s2)


def invalid_private_code_is_rejected():
    user_id, _username = create_user("badprivate")
    _client, socket_client = socket_for(user_id)
    socket_client.emit("join_private_room", {"code": "bad code!"})
    received = events(socket_client)
    messages = [packet["args"][0].get("msg", "") for packet in received if packet["name"] == "queue_status"]
    if not any("Invalid private room code" in message for message in messages):
        raise PlaytestFailure("Invalid private room code was not rejected.")
    disconnect(socket_client)


def disconnect_records_match_end():
    one_id, _one_name = create_user("leaver")
    two_id, two_name = create_user("stayer")
    _c1, s1 = socket_for(one_id)
    _c2, s2 = socket_for(two_id)
    s1.emit("join_queue")
    s2.emit("join_queue")
    socketio.sleep(0.02)
    if not active_matches:
        raise PlaytestFailure("PvP match did not start before disconnect.")
    s1.disconnect()
    socketio.sleep(0.03)
    with app.app_context():
        history = MatchHistory.query.order_by(MatchHistory.id.desc()).first()
        if not history or history.result != "DISCONNECT" or history.winner_name != two_name:
            raise PlaytestFailure("Disconnect did not create expected match history.")
    disconnect(s2)


def no_energy_blocks_card_play():
    user_id, _username = create_user("noenergy")
    _client, socket_client = socket_for(user_id)
    socket_client.emit("join_bot_match")
    assert_started(socket_client)
    match = active_matches[active_room()]
    player = match["p1"]
    player["energy"] = 0
    player["field_m"] = None
    player["field_st"] = None
    socket_client.emit("play_to_field", {"index": 0})
    socketio.sleep(0.01)
    if player["field_m"] or player["field_st"]:
        raise PlaytestFailure("A card was played with zero energy.")
    disconnect(socket_client)


def occupied_monster_zone_blocks_second_monster():
    user_id, _username = create_user("occupied")
    _client, socket_client = socket_for(user_id)
    socket_client.emit("join_bot_match")
    assert_started(socket_client)
    match = active_matches[active_room()]
    player = match["p1"]
    player["energy"] = 10
    player["field_m"] = None
    player["hand"] = [first_monster(), first_monster()]
    socket_client.emit("play_to_field", {"index": 0})
    socketio.sleep(0.01)
    first_field = player["field_m"]
    socket_client.emit("play_to_field", {"index": 0})
    socketio.sleep(0.01)
    if player["field_m"] != first_field or len(player["hand"]) != 1:
        raise PlaytestFailure("Occupied monster zone accepted a second monster.")
    disconnect(socket_client)


def invalid_card_index_is_ignored():
    user_id, _username = create_user("badindex")
    _client, socket_client = socket_for(user_id)
    socket_client.emit("join_bot_match")
    assert_started(socket_client)
    match = active_matches[active_room()]
    player = match["p1"]
    before = len(player["hand"])
    socket_client.emit("play_to_field", {"index": 999})
    socketio.sleep(0.01)
    if len(player["hand"]) != before:
        raise PlaytestFailure("Invalid card index changed the hand.")
    disconnect(socket_client)


def action_rate_limit_triggers():
    user_id, _username = create_user("ratelimit")
    _client, socket_client = socket_for(user_id)
    socket_client.emit("join_bot_match")
    assert_started(socket_client)
    for _ in range(90):
        socket_client.emit("set_intent", {"intent": "Strike"})
    received = events(socket_client)
    messages = [packet["args"][0].get("msg", "") for packet in received if packet["name"] == "queue_status"]
    if not any("Too many actions" in message for message in messages):
        raise PlaytestFailure("Socket action rate limit did not trigger.")
    disconnect(socket_client)


def intent_cycle_is_stable():
    user_id, _username = create_user("intents")
    _client, socket_client = socket_for(user_id)
    socket_client.emit("join_bot_match")
    assert_started(socket_client)
    for intent in ["Strike", "Guard", "Focus"]:
        socket_client.emit("choose_intent", {"intent": intent})
        socketio.sleep(0.01)
        if active_matches[active_room()]["p1"]["intent"] != intent:
            raise PlaytestFailure(f"Intent {intent} was not applied.")
    disconnect(socket_client)


def unleash_toggle_is_stable():
    user_id, _username = create_user("unleash")
    _client, socket_client = socket_for(user_id)
    socket_client.emit("join_bot_match")
    assert_started(socket_client)
    socket_client.emit("toggle_unleash")
    socketio.sleep(0.01)
    if not active_matches:
        raise PlaytestFailure("Unleash toggle crashed the match.")
    disconnect(socket_client)


def same_user_second_tab_is_blocked():
    user_id, _username = create_user("sametab")
    _c1, s1 = socket_for(user_id)
    _c2, s2 = socket_for(user_id)
    s1.emit("join_queue")
    s2.emit("join_queue")
    socketio.sleep(0.02)
    if active_matches:
        raise PlaytestFailure("Same user matched against themselves.")
    received = events(s2)
    messages = [packet["args"][0].get("msg", "") for packet in received if packet["name"] == "queue_status"]
    if not any("another tab" in message for message in messages):
        raise PlaytestFailure("Second tab did not receive queue block message.")
    disconnect(s1, s2)


def cancel_prevents_delayed_fallback():
    user_id, _username = create_user("nofallback")
    _client, socket_client = socket_for(user_id)
    app.config["MATCHMAKING_BOT_FALLBACK_SECONDS"] = 0.04
    socket_client.emit("join_queue")
    socket_client.emit("cancel_queue")
    socketio.sleep(0.1)
    if active_matches or socket_state.get("waiting_player"):
        raise PlaytestFailure("Cancelled queue still produced fallback state.")
    disconnect(socket_client)


def low_hp_bot_match_reaches_game_over():
    user_id, _username = create_user("finishbot")
    _client, socket_client = socket_for(user_id)
    socket_client.emit("join_bot_match")
    assert_started(socket_client)
    match = active_matches[active_room()]
    match["p1"]["field_m"] = first_monster()
    match["p1"]["intent"] = "Strike"
    match["p1"]["energy"] = 10
    match["p2"]["hp"] = 1
    match["p2"]["ready"] = True
    socket_client.emit("declare_ready")
    socketio.sleep(0.03)
    received = events(socket_client)
    game_over = [packet["args"][0] for packet in received if packet["name"] == "game_over"]
    if not game_over or game_over[-1].get("result") != "WIN":
        raise PlaytestFailure("Low HP bot match did not end in a win.")
    disconnect(socket_client)


def pvp_one_round_resolves():
    one_id, _one_name = create_user("roundone")
    two_id, _two_name = create_user("roundtwo")
    _c1, s1 = socket_for(one_id)
    _c2, s2 = socket_for(two_id)
    s1.emit("join_queue")
    s2.emit("join_queue")
    socketio.sleep(0.02)
    room_id = active_room()
    match = active_matches[room_id]
    for player_key in ("p1", "p2"):
        match[player_key]["field_m"] = first_monster()
        match[player_key]["intent"] = "Strike"
        match[player_key]["energy"] = 10
    s1.emit("declare_ready")
    s2.emit("declare_ready")
    socketio.sleep(0.03)
    if room_id in active_matches and active_matches[room_id]["round"] <= 1:
        raise PlaytestFailure("PvP round did not resolve.")
    disconnect(s1, s2)


SCENARIOS = [
    ("training_easy_start", lambda: start_training("easy")),
    ("training_normal_start", lambda: start_training("normal")),
    ("training_hard_start", lambda: start_training("hard")),
    ("bot_button_start", start_bot_button),
    ("pvp_queue_pairs_players", pvp_queue_pairs_players),
    ("queue_falls_back_to_bot", queue_falls_back_to_bot),
    ("cancel_queue", cancel_queue),
    ("private_room_pairs_players", private_room_pairs_players),
    ("invalid_private_code_is_rejected", invalid_private_code_is_rejected),
    ("disconnect_records_match_end", disconnect_records_match_end),
    ("no_energy_blocks_card_play", no_energy_blocks_card_play),
    ("occupied_monster_zone_blocks_second_monster", occupied_monster_zone_blocks_second_monster),
    ("invalid_card_index_is_ignored", invalid_card_index_is_ignored),
    ("action_rate_limit_triggers", action_rate_limit_triggers),
    ("intent_cycle_is_stable", intent_cycle_is_stable),
    ("unleash_toggle_is_stable", unleash_toggle_is_stable),
    ("same_user_second_tab_is_blocked", same_user_second_tab_is_blocked),
    ("cancel_prevents_delayed_fallback", cancel_prevents_delayed_fallback),
    ("low_hp_bot_match_reaches_game_over", low_hp_bot_match_reaches_game_over),
    ("pvp_one_round_resolves", pvp_one_round_resolves),
]


def main():
    app.config.update(TESTING=True, SERVER_NAME="localhost")

    with app.app_context():
        db.drop_all()
        db.create_all()

    failures = []

    for index, (name, scenario) in enumerate(SCENARIOS, start=1):
        reset_runtime()
        try:
            scenario()
            print(f"{index:02d}. PASS {name}")
        except Exception as error:
            failures.append((name, error))
            print(f"{index:02d}. FAIL {name}: {type(error).__name__}: {error}")
        finally:
            reset_runtime()

    print(f"\nArena playtest scenarios: {len(SCENARIOS) - len(failures)}/{len(SCENARIOS)} passed")

    if failures:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
