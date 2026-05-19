from copy import deepcopy

from services.rebirth_bot import choose_response
from services.rebirth_cards import create_card_instance, get_card
from services.rebirth_state import (
    RebirthStateError,
    clear_played_cards,
    create_match,
    draw_to_hand_size,
    remove_from_hand,
)


class RebirthError(ValueError):
    def __init__(self, message, code="rebirth_error"):
        super().__init__(message)
        self.code = code


def start_match(seed=None):
    return create_match(seed=seed)


def compare_power(player_card, bot_card):
    player_power = int(player_card.get("attack", player_card.get("power", 0)) or 0)
    bot_power = int(bot_card.get("attack", bot_card.get("power", 0)) or 0)

    if player_power > bot_power:
        return "player"
    if bot_power > player_power:
        return "bot"
    return "clash"


def calculate_damage(attacker, defender, defender_wounded=False):
    attack = int(attacker.get("attack", attacker.get("power", 0)) or 0)
    guard = int(defender.get("guard", 0) or 0)
    mitigated = max(1, attack - guard // 2)
    if defender_wounded and "wounded" in str(attacker.get("ability_text", "")).lower():
        mitigated += 2
    return mitigated


def apply_turn_damage(match, loser, amount):
    if loser == "player":
        match["player"]["hp"] = max(0, int(match["player"]["hp"]) - amount)
        match["player"]["wounded"] = amount > 0
    elif loser == "bot":
        match["bot"]["hp"] = max(0, int(match["bot"]["hp"]) - amount)
        match["bot"]["wounded"] = amount > 0


def finish_if_needed(match):
    player_hp = int(match["player"]["hp"])
    bot_hp = int(match["bot"]["hp"])

    if player_hp <= 0 and bot_hp <= 0:
        match["winner"] = "clash"
    elif player_hp <= 0:
        match["winner"] = "bot"
    elif bot_hp <= 0:
        match["winner"] = "player"
    else:
        return False

    match["is_finished"] = True
    match["phase"] = "game_over"
    if match["winner"] == "player":
        match["log"].append("Victory. The bot is out of lives.")
    elif match["winner"] == "bot":
        match["log"].append("Defeat. You are out of lives.")
    else:
        match["log"].append("Final clash. Both sides fell together.")
    return True


def resolve_turn(match, player_card, bot_card):
    winner = compare_power(player_card, bot_card)
    if winner == "player":
        damage = calculate_damage(player_card, bot_card, match["bot"].get("wounded", False))
        apply_turn_damage(match, "bot", damage)
        result = {
            "outcome": "Victory",
            "winner": "player",
            "damage": {"player": 0, "bot": damage},
            "message": f"{player_card['name']} overpowers {bot_card['name']}. Bot takes {damage} damage.",
        }
    elif winner == "bot":
        damage = calculate_damage(bot_card, player_card, match["player"].get("wounded", False))
        apply_turn_damage(match, "player", damage)
        result = {
            "outcome": "Defeat",
            "winner": "bot",
            "damage": {"player": damage, "bot": 0},
            "message": f"{bot_card['name']} beats {player_card['name']}. You take {damage} damage.",
        }
    else:
        match["player"]["wounded"] = False
        match["bot"]["wounded"] = False
        result = {
            "outcome": "Clash",
            "winner": None,
            "damage": {"player": 0, "bot": 0},
            "message": f"{player_card['name']} and {bot_card['name']} lock blades. No damage lands.",
        }

    match["result"] = result
    match["last_clash"] = {
        "player_card": deepcopy(player_card),
        "bot_card": deepcopy(bot_card),
        "outcome": result["outcome"],
    }
    match["log"].append(result["message"])
    finish_if_needed(match)
    if not match["is_finished"]:
        match["phase"] = "result"
    return result


def play_card(match, *, card_instance_id=None, card_id=None):
    if match.get("is_finished"):
        raise RebirthError("Match is already finished.", "match_finished")
    if match.get("phase") != "choose":
        raise RebirthError("Advance to the next turn before playing another card.", "turn_not_ready")

    try:
        player_card = remove_from_hand(
            match["player"],
            card_instance_id=card_instance_id,
            card_id=card_id,
        )
    except RebirthStateError as exc:
        raise RebirthError(str(exc), "card_not_in_hand") from exc

    bot_choice = choose_response(match["bot"]["hand"], player_card)
    if not bot_choice:
        raise RebirthError("Bot has no card to answer with.", "bot_hand_empty")

    bot_card = remove_from_hand(match["bot"], card_instance_id=bot_choice["instance_id"])
    match["player"]["played_card"] = player_card
    match["bot"]["played_card"] = bot_card
    turn_label = f"Turn {match['turn']:02d}"
    match["log"].append(f"{turn_label}   You played {player_card['name']}.")
    match["log"].append(f"{turn_label}   Bot played {bot_card['name']}.")
    resolve_turn(match, player_card, bot_card)
    return match


def evolve_duplicate(match, card_id):
    if match.get("is_finished"):
        raise RebirthError("Match is already finished.", "match_finished")
    if match.get("phase") != "choose":
        raise RebirthError("Evolution is only available before playing a card.", "evolution_not_ready")
    if not card_id:
        raise RebirthError("card_id is required.", "missing_card_id")

    try:
        card = get_card(card_id)
    except ValueError as exc:
        raise RebirthError(str(exc), "unknown_card") from exc

    evolution_id = card.get("evolution_id")
    if not evolution_id:
        raise RebirthError("This monster has no MVP evolution.", "no_evolution")

    matches = [hand_card for hand_card in match["player"]["hand"] if hand_card["id"] == card_id]
    if len(matches) < 2:
        raise RebirthError("Two matching monsters are required to evolve.", "duplicate_required")

    consumed = []
    for _ in range(2):
        consumed.append(remove_from_hand(match["player"], card_id=card_id))
    for consumed_card in consumed:
        match["player"]["discard"].append(consumed_card)

    sequence = len(match["player"]["deck"]) + len(match["player"]["hand"]) + len(match["player"]["discard"]) + 1
    evolved = create_card_instance(evolution_id, "player", sequence)
    evolved["evolved_from"] = [consumed_card["instance_id"] for consumed_card in consumed]
    match["player"]["hand"].insert(0, evolved)
    match["log"].append(f"Turn {match['turn']:02d}   {card['name']} x2 evolved into {evolved['name']}.")
    return deepcopy(evolved)


def next_turn(match):
    if match.get("is_finished"):
        return match
    if match.get("phase") == "choose":
        return match

    clear_played_cards(match)
    match["turn"] += 1
    draw_to_hand_size(match["player"])
    draw_to_hand_size(match["bot"])
    match["result"] = None
    match["last_clash"] = None
    match["phase"] = "choose"
    match["log"].append(f"Turn {match['turn']:02d}   Choose one monster.")
    return match
