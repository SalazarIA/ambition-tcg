import json
import os
import random

import itsdangerous
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_socketio import SocketIO, join_room
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config
from game.battle import resolve_battle
from game.cards import CARD_CATALOG, card_sort_key
from game.deck import (
    build_playable_deck,
    collection_summary,
    deck_summary,
    draw_starting_hand,
    load_card_ids,
    validate_deck,
)
from models import MatchHistory, User, db


app = Flask(__name__)
app.config.from_object(Config)

app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_for=1,
    x_proto=1,
    x_host=1,
    x_port=1,
    x_prefix=1,
)

db.init_app(app)

socketio = SocketIO(
    app,
    async_mode="threading",
    cors_allowed_origins="*",
    manage_session=False,
)

serializer = itsdangerous.URLSafeTimedSerializer(app.config["SECRET_KEY"])

active_matches = {}
player_rooms = {}
waiting_player = None


def create_database_tables():
    with app.app_context():
        db.create_all()


create_database_tables()


def current_user():
    if "user_id" not in session:
        return None

    return db.session.get(User, session["user_id"])


def login_required_redirect():
    if "user_id" not in session:
        return redirect("/login")

    user = current_user()

    if not user:
        session.clear()
        return redirect("/login")

    return None


def booster_pull():
    roll = random.random()

    if roll < 0.78:
        rarity = "Common"
    else:
        rarity = "Uncommon"

    pool = [card for card in CARD_CATALOG if card["rarity"] == rarity]

    if not pool:
        pool = CARD_CATALOG

    return random.choice(pool).copy()


def parse_battle_logs(match):
    logs = match.get("logs", [])

    if not isinstance(logs, list):
        return []

    clean_logs = []

    for item in logs[-80:]:
        clean_logs.append(str(item)[:500])

    return clean_logs


def save_match_history(room_id, winner_key):
    match = active_matches.get(room_id)

    if not match:
        return

    p1 = match["p1"]
    p2 = match["p2"]

    winner_id = None
    winner_name = None
    result = "DRAW"

    if winner_key == "p1":
        winner_id = p1["user_id"]
        winner_name = p1["name"]
        result = "P1_WIN"

    elif winner_key == "p2":
        winner_id = p2["user_id"]
        winner_name = p2["name"]
        result = "P2_WIN"

    elif winner_key == "DRAW":
        result = "DRAW"

    history = MatchHistory(
        player1_id=p1["user_id"],
        player2_id=p2["user_id"],
        winner_id=winner_id,
        player1_name=p1["name"],
        player2_name=p2["name"],
        winner_name=winner_name,
        result=result,
        player1_final_hp=int(p1.get("hp", 0)),
        player2_final_hp=int(p2.get("hp", 0)),
        total_rounds=max(0, int(match.get("round", 1)) - 1),
        battle_log_json=json.dumps(parse_battle_logs(match)),
    )

    db.session.add(history)
    db.session.commit()


@app.route("/")
def index():
    user = current_user()
    return render_template("index.html", user=user)


@app.route("/offline")
def offline():
    return render_template("offline.html")


@app.route("/health")
def health():
    return {
        "status": "ok",
        "app": "Ambition TCG",
        "version": "beta-profile-0.3",
        "environment": app.config["ENVIRONMENT"],
    }


@app.route("/profile")
def profile():
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()

    recent_matches = (
        MatchHistory.query
        .filter(
            (MatchHistory.player1_id == user.id)
            | (MatchHistory.player2_id == user.id)
        )
        .order_by(MatchHistory.created_at.desc())
        .limit(10)
        .all()
    )

    collection_ids = load_card_ids(user.collection_json)
    deck_ids = load_card_ids(user.deck_json)

    owned_cards = len(collection_ids)
    deck_size = len(deck_ids)

    return render_template(
        "profile.html",
        user=user,
        recent_matches=recent_matches,
        owned_cards=owned_cards,
        deck_size=deck_size,
    )


@app.route("/ranking")
def ranking():
    users = (
        User.query
        .order_by(
            User.wins.desc(),
            User.losses.asc(),
            User.coins.desc(),
            User.username.asc(),
        )
        .limit(100)
        .all()
    )

    return render_template(
        "ranking.html",
        user=current_user(),
        users=users,
    )


@app.route("/match-history")
def match_history():
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()

    matches = (
        MatchHistory.query
        .filter(
            (MatchHistory.player1_id == user.id)
            | (MatchHistory.player2_id == user.id)
        )
        .order_by(MatchHistory.created_at.desc())
        .limit(50)
        .all()
    )

    return render_template(
        "match_history.html",
        user=user,
        matches=matches,
        json=json,
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        if not username or not email or not password:
            flash("Fill all fields.")
            return redirect("/register")

        if len(password) < 6:
            flash("Password must have at least 6 characters.")
            return redirect("/register")

        if User.query.filter_by(email=email).first():
            flash("Email already exists.")
            return redirect("/register")

        if User.query.filter_by(username=username).first():
            flash("Username already exists.")
            return redirect("/register")

        new_user = User(
            username=username,
            email=email,
        )
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        token = serializer.dumps(email, salt="email-confirm")
        verification_url = url_for("confirm_email", token=token, _external=True)

        print("\n--- AMBITION VERIFICATION LINK ---")
        print(verification_url)
        print("----------------------------------\n")

        flash("Registered. Check your server terminal/logs for the verification link.")
        return redirect("/login")

    return render_template("register.html")


@app.route("/confirm_email/<token>")
def confirm_email(token):
    try:
        email = serializer.loads(token, salt="email-confirm", max_age=3600)
    except Exception:
        return "Verification link expired."

    user = User.query.filter_by(email=email).first_or_404()
    user.is_verified = True

    db.session.commit()

    flash("Account verified. You can login now.")
    return redirect("/login")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash("Invalid login.")
            return redirect("/login")

        if not user.is_verified:
            flash("Verify your email first. Check the verification link in server logs.")
            return redirect("/login")

        session["user_id"] = user.id
        return redirect("/")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/collection")
def collection():
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()
    collection_ids = load_card_ids(user.collection_json)
    cards = collection_summary(collection_ids)
    cards = sorted(cards, key=card_sort_key)

    return render_template("collection.html", user=user, cards=cards)


@app.route("/shop", methods=["GET", "POST"])
def shop():
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()
    pulled_cards = []

    if request.method == "POST":
        pack_cost = 300

        if user.coins < pack_cost:
            flash("Not enough coins.")
            return redirect("/shop")

        user.coins -= pack_cost

        collection_ids = load_card_ids(user.collection_json)

        for _ in range(5):
            card = booster_pull()
            pulled_cards.append(card)
            collection_ids.append(card["id"])

        user.collection_json = json.dumps(collection_ids)
        db.session.commit()

    return render_template("shop.html", user=user, pulled_cards=pulled_cards)


@app.route("/deck-builder", methods=["GET", "POST"])
def deck_builder():
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()

    collection_ids = load_card_ids(user.collection_json)
    deck_ids = load_card_ids(user.deck_json)

    if request.method == "POST":
        selected_cards = request.form.getlist("deck_cards")
        errors = validate_deck(selected_cards, collection_ids)

        if errors:
            for error in errors:
                flash(error)
        else:
            user.deck_json = json.dumps(selected_cards)
            db.session.commit()
            flash("Deck saved successfully.")

        return redirect("/deck-builder")

    collection_cards = sorted(collection_summary(collection_ids), key=card_sort_key)
    current_deck = sorted(deck_summary(deck_ids), key=card_sort_key)

    deck_validation_errors = validate_deck(deck_ids, collection_ids)

    return render_template(
        "deck_builder.html",
        user=user,
        collection_cards=collection_cards,
        current_deck=current_deck,
        deck_ids=deck_ids,
        deck_validation_errors=deck_validation_errors,
    )


@app.route("/arena")
def arena():
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()
    collection_ids = load_card_ids(user.collection_json)
    deck_ids = load_card_ids(user.deck_json)
    errors = validate_deck(deck_ids, collection_ids)

    if errors:
        flash("Your deck is invalid. Fix it before entering the arena.")
        return redirect("/deck-builder")

    return render_template("arena.html", user=user)


def find_player_key(match, sid):
    if match["p1"]["sid"] == sid:
        return "p1"

    if match["p2"]["sid"] == sid:
        return "p2"

    return None


def emit_log(room_id, message):
    match = active_matches.get(room_id)

    if match is not None:
        match.setdefault("logs", [])
        match["logs"].append(str(message))

    socketio.emit("battle_log", {"msg": message}, to=room_id)


def emit_state(room_id):
    match = active_matches.get(room_id)

    if not match:
        return

    for player_key, enemy_key in [("p1", "p2"), ("p2", "p1")]:
        player = match[player_key]
        enemy = match[enemy_key]

        enemy_monster_status = "EMPTY"

        if enemy.get("field_m"):
            enemy_monster_status = "REVEALED" if match["resolving"] else "HIDDEN"

        enemy_st_status = "EMPTY"

        if enemy.get("field_st"):
            enemy_st_status = "SET"

        state = {
            "room_id": room_id,
            "round": match["round"],
            "resolving": match["resolving"],
            "me": {
                "name": player["name"],
                "hp": player["hp"],
                "deck_count": len(player["deck"]),
                "graveyard_count": len(player["graveyard"]),
                "hand": player["hand"],
                "field_m": player["field_m"],
                "field_st": player["field_st"],
                "ready": player["ready"],
            },
            "enemy": {
                "name": enemy["name"],
                "hp": enemy["hp"],
                "deck_count": len(enemy["deck"]),
                "graveyard_count": len(enemy["graveyard"]),
                "hand_count": len(enemy["hand"]),
                "ready": enemy["ready"],
                "field_m_status": enemy_monster_status,
                "field_m_rev": enemy["field_m"] if match["resolving"] else None,
                "field_st_status": enemy_st_status,
            },
        }

        socketio.emit("game_state_update", state, to=player["sid"])


def create_player_object(user, sid):
    deck = build_playable_deck(user.deck_json)
    hand = draw_starting_hand(deck, 5)

    return {
        "sid": sid,
        "user_id": user.id,
        "name": user.username,
        "hp": 4000,
        "deck": deck,
        "hand": hand,
        "graveyard": [],
        "field_m": None,
        "field_st": None,
        "ready": False,
        "shield": 0,
    }


def end_match(room_id, winner_key):
    match = active_matches.get(room_id)

    if not match:
        return

    p1 = match["p1"]
    p2 = match["p2"]

    save_match_history(room_id, winner_key)

    if winner_key == "DRAW":
        socketio.emit("game_over", {"result": "DRAW"}, to=p1["sid"])
        socketio.emit("game_over", {"result": "DRAW"}, to=p2["sid"])
    else:
        loser_key = "p2" if winner_key == "p1" else "p1"

        winner = match[winner_key]
        loser = match[loser_key]

        socketio.emit("game_over", {"result": "WIN"}, to=winner["sid"])
        socketio.emit("game_over", {"result": "LOSE"}, to=loser["sid"])

        winner_user = db.session.get(User, winner["user_id"])
        loser_user = db.session.get(User, loser["user_id"])

        if winner_user:
            winner_user.wins += 1
            winner_user.coins += 150

        if loser_user:
            loser_user.losses += 1

        db.session.commit()

    player_rooms.pop(p1["sid"], None)
    player_rooms.pop(p2["sid"], None)
    active_matches.pop(room_id, None)


@socketio.on("join_queue")
def handle_join_queue():
    global waiting_player

    user_id = session.get("user_id")

    if not user_id:
        return

    user = db.session.get(User, user_id)

    if not user:
        return

    current_sid = request.sid

    if current_sid in player_rooms:
        return

    player_object = create_player_object(user, current_sid)

    if waiting_player is None:
        waiting_player = player_object
        socketio.emit("queue_status", {"msg": "Searching for opponent..."}, to=current_sid)
        return

    if waiting_player["sid"] == current_sid:
        return

    room_id = f"room_{waiting_player['sid']}_{current_sid}"

    join_room(room_id, sid=waiting_player["sid"])
    join_room(room_id, sid=current_sid)

    active_matches[room_id] = {
        "p1": waiting_player,
        "p2": player_object,
        "round": 1,
        "resolving": False,
        "logs": [],
    }

    player_rooms[waiting_player["sid"]] = room_id
    player_rooms[current_sid] = room_id

    socketio.emit("match_found", {"msg": "Opponent found. Duel started."}, to=room_id)

    waiting_player = None

    emit_log(room_id, "Match started.")
    emit_state(room_id)


@socketio.on("play_to_field")
def play_to_field(data):
    room_id = player_rooms.get(request.sid)

    if not room_id:
        return

    match = active_matches.get(room_id)

    if not match or match["resolving"]:
        return

    player_key = find_player_key(match, request.sid)

    if not player_key:
        return

    player = match[player_key]

    if player["ready"]:
        return

    try:
        index = int(data.get("index"))
    except Exception:
        return

    if index < 0 or index >= len(player["hand"]):
        return

    card = player["hand"][index]
    card_type = card.get("type")

    if card_type == "Monster":
        if player["field_m"] is not None:
            emit_log(room_id, f"{player['name']} tried to play another monster, but the monster zone is occupied.")
            return

        player["field_m"] = player["hand"].pop(index)
        emit_log(room_id, f"{player['name']} set a monster.")

    elif card_type in ["Spell", "Trap"]:
        if player["field_st"] is not None:
            emit_log(room_id, f"{player['name']} tried to play another spell/trap, but the zone is occupied.")
            return

        player["field_st"] = player["hand"].pop(index)
        emit_log(room_id, f"{player['name']} set a spell/trap.")

    emit_state(room_id)


@socketio.on("declare_ready")
def declare_ready():
    room_id = player_rooms.get(request.sid)

    if not room_id:
        return

    match = active_matches.get(room_id)

    if not match or match["resolving"]:
        return

    player_key = find_player_key(match, request.sid)

    if not player_key:
        return

    player = match[player_key]
    player["ready"] = True

    emit_log(room_id, f"{player['name']} is ready.")
    emit_state(room_id)

    if match["p1"]["ready"] and match["p2"]["ready"]:
        battle_result = resolve_battle(match)

        for log_message in battle_result["logs"]:
            emit_log(room_id, log_message)

        emit_state(room_id)

        if battle_result["winner"]:
            end_match(room_id, battle_result["winner"])


@socketio.on("disconnect")
def handle_disconnect():
    global waiting_player

    sid = request.sid

    if waiting_player and waiting_player["sid"] == sid:
        waiting_player = None
        return

    room_id = player_rooms.get(sid)

    if not room_id:
        return

    match = active_matches.get(room_id)

    if not match:
        return

    player_key = find_player_key(match, sid)

    if not player_key:
        return

    enemy_key = "p2" if player_key == "p1" else "p1"
    enemy = match[enemy_key]

    socketio.emit("opponent_left", {"msg": "Opponent disconnected. You win."}, to=enemy["sid"])

    end_match(room_id, enemy_key)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))

    socketio.run(
        app,
        debug=app.config["DEBUG_MODE"],
        host="0.0.0.0",
        port=port,
        allow_unsafe_werkzeug=True,
    )
