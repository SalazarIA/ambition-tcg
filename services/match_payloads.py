from game.match_utils import player_display_name


def find_player_key(match, sid):
    if match["p1"]["sid"] == sid:
        return "p1"

    if match["p2"]["sid"] == sid:
        return "p2"

    return None


def match_mode(match):
    if match.get("matchmaking_fallback"):
        return "fallback_bot"

    if match.get("training"):
        return "training"

    if match.get("is_bot_match"):
        return "bot"

    return "pvp"


def perspective_battle_events(events, player_key):
    if player_key == "p1":
        return [dict(event) for event in events]

    side_map = {
        "player": "enemy",
        "enemy": "player",
    }

    perspective_events = []

    for event in events:
        mapped_event = dict(event)

        for key in ["side", "to", "from"]:
            value = mapped_event.get(key)

            if value in side_map:
                mapped_event[key] = side_map[value]

        perspective_events.append(mapped_event)

    return perspective_events


def build_game_state_payloads(room_id, match):
    payloads = []

    for player_key, enemy_key in [("p1", "p2"), ("p2", "p1")]:
        player = match[player_key]
        enemy = match[enemy_key]

        if player.get("is_bot"):
            continue

        enemy_monster_status = "EMPTY"

        if enemy.get("field_m"):
            enemy_monster_status = "REVEALED" if match["resolving"] else "HIDDEN"

        enemy_st_status = "EMPTY"

        if enemy.get("field_st"):
            enemy_st_status = "SET"

        enemy_intent = enemy.get("intent", "Strike") if match.get("resolving") else "Hidden"

        payloads.append((
            player["sid"],
            {
                "room_id": room_id,
                "round": match["round"],
                "phase": match.get("phase", "Set Phase"),
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
                    "energy": player.get("energy", 0),
                    "max_energy": player.get("max_energy", 0),
                    "ambition": player.get("ambition", 0),
                    "ambition_unleashed": player.get("ambition_unleashed", False),
                    "wants_unleash": player.get("wants_unleash", False),
                    "overreach_count": player.get("overreach_count", 0),
                    "intent": player.get("intent", "Strike"),
                },
                "enemy": {
                    "name": enemy["name"],
                    "hp": enemy["hp"],
                    "deck_count": len(enemy["deck"]),
                    "graveyard_count": len(enemy["graveyard"]),
                    "hand_count": len(enemy["hand"]),
                    "ready": enemy["ready"],
                    "energy": enemy.get("energy", 0),
                    "max_energy": enemy.get("max_energy", 0),
                    "ambition": enemy.get("ambition", 0),
                    "ambition_unleashed": enemy.get("ambition_unleashed", False),
                    "wants_unleash": enemy.get("wants_unleash", False),
                    "overreach_count": enemy.get("overreach_count", 0),
                    "intent": enemy_intent,
                    "field_m_status": enemy_monster_status,
                    "field_m_rev": enemy["field_m"] if match["resolving"] else None,
                    "field_st_status": enemy_st_status,
                },
            },
        ))

    return payloads


def build_post_match_payload(match, viewer_key, result, rewards):
    try:
        p1 = match.get("p1", {})
        p2 = match.get("p2", {})

        opponent_key = "p2" if viewer_key == "p1" else "p1"
        viewer = match.get(viewer_key, {})
        opponent = match.get(opponent_key, {})

        return {
            "result": result,
            "mode": match_mode(match),
            "bot_difficulty": match.get("bot_difficulty"),
            "rounds": int(match.get("round", 1) or 1),
            "rewards": rewards or {"coins": 0, "xp": 0},
            "viewer": {
                "name": player_display_name(viewer),
                "hp": _safe_hp(viewer),
            },
            "opponent": {
                "name": player_display_name(opponent),
                "hp": _safe_hp(opponent),
            },
            "players": {
                "p1": {
                    "name": player_display_name(p1),
                    "hp": _safe_hp(p1),
                },
                "p2": {
                    "name": player_display_name(p2),
                    "hp": _safe_hp(p2),
                },
            },
            "summary": {
                "title": "Victory" if result == "WIN" else "Defeat" if result == "LOSE" else "Draw",
                "message": "You won the duel." if result == "WIN" else "You were defeated." if result == "LOSE" else "The duel ended in a draw.",
            },
        }
    except Exception as error:
        print("V1.07 POST MATCH PAYLOAD ERROR:", type(error).__name__, error)
        return {
            "result": result,
            "mode": match_mode(match),
            "rounds": int(match.get("round", 1) or 1),
            "rewards": rewards or {"coins": 0, "xp": 0},
            "summary": {
                "title": result,
                "message": "Match finished.",
            },
        }


def _safe_hp(player):
    try:
        return max(0, int(player.get("hp", 0) or 0))
    except Exception:
        return 0


def history_result_for_ending(winner_key, ending_reason):
    if winner_key == "DRAW":
        return "DRAW"

    if ending_reason and ending_reason != "completed":
        return str(ending_reason).upper()[:20]

    return "FINISHED"
