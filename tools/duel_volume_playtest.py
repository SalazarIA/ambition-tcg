import json
import os
import random
import statistics
import sys
import tempfile
import time
import uuid
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ["DATABASE_URL"] = os.environ.get(
    "DUEL_VOLUME_DATABASE_URL",
    f"sqlite:///{Path(tempfile.gettempdir()) / ('ambition_duel_volume_' + uuid.uuid4().hex + '.db')}",
)
os.environ.setdefault("SECRET_KEY", "duel-volume-playtest-secret-key")
os.environ.setdefault("WTF_CSRF_ENABLED", "true")
os.environ.setdefault("BETA_AUTO_VERIFY", "true")
os.environ.setdefault("MATCHMAKING_BOT_FALLBACK_SECONDS", "30")
os.environ.setdefault("ENVIRONMENT", "testing")

from app import (  # noqa: E402
    active_matches,
    app,
    db,
    private_waiting_rooms,
    player_rooms,
    socket_event_hits,
    socket_state,
    socketio,
)
from models import MatchHistory, User  # noqa: E402


RNG = random.Random(20260507)
PVP_MATCHES = int(os.environ.get("DUEL_VOLUME_PVP_MATCHES", "50"))
BOT_MATCHES = int(os.environ.get("DUEL_VOLUME_BOT_MATCHES", "50"))
MAX_ROUNDS = int(os.environ.get("DUEL_VOLUME_MAX_ROUNDS", "60"))
PASSWORD = "StrongPass1"
INTENT_WEIGHTS = {
    "default": [("Strike", 58), ("Guard", 22), ("Focus", 20)],
    "low_hp": [("Strike", 42), ("Guard", 38), ("Focus", 20)],
    "high_ambition": [("Strike", 65), ("Guard", 20), ("Focus", 15)],
}


class VolumePlaytestFailure(AssertionError):
    pass


def reset_runtime():
    active_matches.clear()
    player_rooms.clear()
    private_waiting_rooms.clear()
    socket_event_hits.clear()
    socket_state["waiting_player"] = None
    socket_state["waiting_since"] = None
    socket_state["waiting_deck_json"] = None
    socket_state["queue_generation"] = int(socket_state.get("queue_generation", 0) or 0) + 1
    socket_state.setdefault("online_players", {}).clear()


def create_account(label):
    suffix = uuid.uuid4().hex[:8]
    user = User(
        username=f"{label}_{suffix}",
        email=f"{label}_{suffix}@playtest.local",
        account_status="active",
        is_verified=True,
    )
    user.set_password(PASSWORD)
    db.session.add(user)
    db.session.commit()
    return user.id, user.username, user.email


def socket_for(user_id):
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["_csrf_token"] = f"duel-volume-{user_id}-{uuid.uuid4().hex[:6]}"

    socket_client = socketio.test_client(app, flask_test_client=client)

    if not socket_client.is_connected():
        raise VolumePlaytestFailure(f"Socket did not connect for user_id={user_id}.")

    socket_client.get_received()
    return client, socket_client


def disconnect(*socket_clients):
    for socket_client in socket_clients:
        try:
            if socket_client and socket_client.is_connected():
                socket_client.disconnect()
        except Exception:
            pass


def received_issues(received):
    issues = []

    for packet in received:
        name = packet.get("name")
        payload = (packet.get("args") or [{}])[0] or {}

        if name == "action_error":
            issues.append(f"action_error:{payload.get('code') or payload.get('message')}")
            continue

        if name == "queue_status":
            message = str(payload.get("msg") or "")
            lowered = message.lower()
            if any(token in lowered for token in ["failed", "too many", "invalid", "could not"]):
                issues.append(f"queue_status:{message}")

    return issues


def active_room():
    if not active_matches:
        raise VolumePlaytestFailure("Expected active match.")

    return next(iter(active_matches.keys()))


def choose_intent(player):
    if int(player.get("hp") or 0) <= 1200:
        bucket = "low_hp"
    elif int(player.get("ambition") or 0) >= 4:
        bucket = "high_ambition"
    else:
        bucket = "default"

    intents, weights = zip(*INTENT_WEIGHTS[bucket])
    return RNG.choices(intents, weights=weights, k=1)[0]


def card_cost(card):
    try:
        return int(card.get("cost") or 1)
    except Exception:
        return 1


def card_power(card):
    try:
        return int(card.get("power") or card.get("attack") or card.get("value") or 0)
    except Exception:
        return 0


def card_score(card):
    value = card_power(card)
    value += int(card.get("value") or 0) if str(card.get("type")) != "Monster" else 0
    value -= card_cost(card) * 8
    return value


def best_affordable_index(player, wanted_slot):
    if wanted_slot == "monster" and player.get("field_m"):
        return None

    if wanted_slot == "support" and player.get("field_st"):
        return None

    energy = int(player.get("energy") or 0)
    candidates = []

    for index, card in enumerate(player.get("hand") or []):
        card_type = card.get("type")

        if wanted_slot == "monster" and card_type != "Monster":
            continue

        if wanted_slot == "support" and card_type not in {"Spell", "Trap"}:
            continue

        if card_cost(card) <= energy:
            candidates.append((card_score(card), index, card))

    if not candidates:
        return None

    candidates.sort(reverse=True, key=lambda item: (item[0], -item[1]))
    return candidates[0][1]


def play_slot(socket_client, match, player_key, slot):
    player = match[player_key]
    index = best_affordable_index(player, slot)

    if index is None:
        return False

    socket_client.emit("play_to_field", {"index": index})
    socketio.sleep(0.001)
    return True


def take_turn(socket_client, match, player_key):
    player = match[player_key]

    if int(player.get("ambition") or 0) >= 5 and player.get("field_m") and RNG.random() < 0.18:
        socket_client.emit("toggle_unleash")
        socketio.sleep(0.001)

    socket_client.emit("choose_intent", {"intent": choose_intent(player)})
    socketio.sleep(0.001)

    # Try monster first, then a spell/trap with remaining energy.
    play_slot(socket_client, match, player_key, "monster")
    play_slot(socket_client, match, player_key, "support")

    socket_client.emit("declare_ready")
    socketio.sleep(0.003)


def summarize_history(history, match_type, index, expected_names):
    winner = history.winner_name or "DRAW"
    player1 = history.player1_name
    player2 = history.player2_name

    if match_type == "pvp" and {player1, player2} != set(expected_names):
        raise VolumePlaytestFailure(f"Unexpected PvP players: {player1} vs {player2}.")

    if match_type == "bot" and "Ambitionz Bot" not in {player1, player2}:
        raise VolumePlaytestFailure(f"Unexpected bot match players: {player1} vs {player2}.")

    return {
        "index": index,
        "type": match_type,
        "winner": winner,
        "player1": player1,
        "player2": player2,
        "rounds": int(history.total_rounds or 0),
        "p1_hp": int(history.player1_final_hp or 0),
        "p2_hp": int(history.player2_final_hp or 0),
        "result": history.result,
    }


def play_pvp(index, account_a, account_b):
    reset_runtime()
    _client_a, socket_a = socket_for(account_a["id"])
    _client_b, socket_b = socket_for(account_b["id"])
    started_history_id = latest_history_id()

    try:
        socket_a.emit("join_queue")
        socketio.sleep(0.002)
        socket_b.emit("join_queue")
        socketio.sleep(0.01)

        room_id = active_room()
        rounds_seen = set()

        for _ in range(MAX_ROUNDS):
            if room_id not in active_matches:
                break

            match = active_matches[room_id]
            rounds_seen.add(match.get("round"))
            take_turn(socket_a, match, "p1")

            if room_id not in active_matches:
                break

            match = active_matches[room_id]
            take_turn(socket_b, match, "p2")
            socketio.sleep(0.004)

        if room_id in active_matches:
            raise VolumePlaytestFailure(f"PvP match {index} exceeded {MAX_ROUNDS} rounds.")

        history = next_history_after(started_history_id)
        result = summarize_history(history, "pvp", index, (account_a["username"], account_b["username"]))
        result["rounds_seen"] = len(rounds_seen)
        result["issues"] = received_issues(socket_a.get_received()) + received_issues(socket_b.get_received())
        return result
    finally:
        disconnect(socket_a, socket_b)
        reset_runtime()


def play_bot(index, account):
    reset_runtime()
    _client, socket_client = socket_for(account["id"])
    started_history_id = latest_history_id()

    try:
        socket_client.emit("join_bot_match")
        socketio.sleep(0.01)

        room_id = active_room()
        rounds_seen = set()

        for _ in range(MAX_ROUNDS):
            if room_id not in active_matches:
                break

            match = active_matches[room_id]
            rounds_seen.add(match.get("round"))
            take_turn(socket_client, match, "p1")
            socketio.sleep(0.004)

        if room_id in active_matches:
            raise VolumePlaytestFailure(f"Bot match {index} exceeded {MAX_ROUNDS} rounds.")

        history = next_history_after(started_history_id)
        result = summarize_history(history, "bot", index, (account["username"], "Ambitionz Bot"))
        result["human"] = account["username"]
        result["rounds_seen"] = len(rounds_seen)
        result["issues"] = received_issues(socket_client.get_received())
        return result
    finally:
        disconnect(socket_client)
        reset_runtime()


def latest_history_id():
    history = MatchHistory.query.order_by(MatchHistory.id.desc()).first()
    return int(history.id) if history else 0


def next_history_after(history_id):
    history = MatchHistory.query.filter(MatchHistory.id > history_id).order_by(MatchHistory.id.asc()).first()

    if not history:
        raise VolumePlaytestFailure("Match ended without MatchHistory record.")

    return history


def stat_block(results, account_names):
    rounds = [item["rounds"] for item in results]
    winners = Counter(item["winner"] for item in results)
    issues = [issue for item in results for issue in item.get("issues", [])]
    hp_by_winner = defaultdict(list)

    for item in results:
        if item["winner"] == item["player1"]:
            hp_by_winner[item["winner"]].append(item["p1_hp"])
        elif item["winner"] == item["player2"]:
            hp_by_winner[item["winner"]].append(item["p2_hp"])

    return {
        "matches": len(results),
        "wins": dict(winners),
        "account_wins": {name: winners.get(name, 0) for name in account_names},
        "draws": winners.get("DRAW", 0),
        "avg_rounds": round(statistics.mean(rounds), 2) if rounds else 0,
        "median_rounds": round(statistics.median(rounds), 2) if rounds else 0,
        "min_rounds": min(rounds) if rounds else 0,
        "max_rounds": max(rounds) if rounds else 0,
        "issues": Counter(issues),
        "winner_avg_hp": {
            winner: round(statistics.mean(values), 1)
            for winner, values in hp_by_winner.items()
            if values
        },
    }


def print_section(title):
    print(f"\n=== {title} ===")


def main():
    started_at = time.time()
    app.config.update(TESTING=True, SERVER_NAME="localhost", MATCHMAKING_BOT_FALLBACK_SECONDS=30)

    with app.app_context():
        db.drop_all()
        db.create_all()
        reset_runtime()

        account_a_id, account_a_name, account_a_email = create_account("volume_alpha")
        account_b_id, account_b_name, account_b_email = create_account("volume_beta")

        account_a = {"id": account_a_id, "username": account_a_name, "email": account_a_email}
        account_b = {"id": account_b_id, "username": account_b_name, "email": account_b_email}

        pvp_results = []
        bot_results = []
        failures = []

        print_section("Accounts")
        print(json.dumps({"account_a": account_a, "account_b": account_b}, indent=2, sort_keys=True))

        print_section(f"PvP {PVP_MATCHES} matches")
        for index in range(1, PVP_MATCHES + 1):
            try:
                result = play_pvp(index, account_a, account_b)
                pvp_results.append(result)
                print(f"PVP {index:02d}: winner={result['winner']} rounds={result['rounds']} hp={result['p1_hp']}/{result['p2_hp']}")
            except Exception as error:
                failures.append({"type": "pvp", "index": index, "error": f"{type(error).__name__}: {error}"})
                print(f"PVP {index:02d}: FAIL {type(error).__name__}: {error}")

        print_section(f"Bot {BOT_MATCHES} matches")
        for index in range(1, BOT_MATCHES + 1):
            account = account_a if index % 2 else account_b

            try:
                result = play_bot(index, account)
                bot_results.append(result)
                print(f"BOT {index:02d}: human={account['username']} winner={result['winner']} rounds={result['rounds']} hp={result['p1_hp']}/{result['p2_hp']}")
            except Exception as error:
                failures.append({"type": "bot", "index": index, "error": f"{type(error).__name__}: {error}"})
                print(f"BOT {index:02d}: FAIL {type(error).__name__}: {error}")

        account_names = [account_a_name, account_b_name]
        summary = {
            "accounts": {"account_a": account_a, "account_b": account_b},
            "requested": {"pvp": PVP_MATCHES, "bot": BOT_MATCHES},
            "completed": {"pvp": len(pvp_results), "bot": len(bot_results)},
            "pvp": stat_block(pvp_results, account_names),
            "bot": stat_block(bot_results, [account_a_name, account_b_name, "Ambitionz Bot"]),
            "failures": failures,
            "history_rows": MatchHistory.query.count(),
            "duration_seconds": round(time.time() - started_at, 2),
        }

        print_section("Summary JSON")
        print(json.dumps(summary, indent=2, sort_keys=True))

        if failures:
            return 1

        if len(pvp_results) != PVP_MATCHES or len(bot_results) != BOT_MATCHES:
            return 1

        return 0


if __name__ == "__main__":
    raise SystemExit(main())
