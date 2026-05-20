from copy import deepcopy
import hashlib


BOT_PERSONALITY_ORDER = ("defensive", "aggressive", "opportunist")

BOT_PERSONALITIES = {
    "defensive": {
        "id": "defensive",
        "name": "Defensive Bot",
        "copy": "Prioritizes guard and stable answers before damage spikes.",
        "policy": "win with guarded bodies; otherwise absorb with the highest guard",
    },
    "aggressive": {
        "id": "aggressive",
        "name": "Aggressive Bot",
        "copy": "Pushes the highest attack line and tries to end clashes quickly.",
        "policy": "play the highest attack available, preferring winning attacks",
    },
    "opportunist": {
        "id": "opportunist",
        "name": "Opportunist Bot",
        "copy": "Looks for ability swings, finishers and pressure windows.",
        "policy": "prefer ability swing cards, then the smallest clean win",
    },
}

ABILITY_PRIORITIES = {
    "bleed_mark": 8,
    "fade_cut": 7,
    "inferno_bite": 7,
    "apex_rend": 7,
    "storm_dive": 6,
    "silent_pursuit": 6,
    "rending_strike": 5,
    "molten_bite": 4,
    "fortress_hit": 4,
    "immovable": 3,
    "bulwark": 3,
    "brace": 2,
    "high_guard": 2,
}


def card_attack(card):
    return int(card.get("attack", card.get("power", 0)) or 0)


def card_guard(card):
    return int(card.get("guard", 0) or 0)


def ability_priority(card):
    return ABILITY_PRIORITIES.get(str(card.get("ability_key") or ""), 0)


def normalize_personality(profile_id=None):
    profile_id = str(profile_id or "defensive").strip().lower()
    if profile_id not in BOT_PERSONALITIES:
        return "defensive"
    return profile_id


def personality_payload(profile_id=None):
    return deepcopy(BOT_PERSONALITIES[normalize_personality(profile_id)])


def choose_personality(seed=None, match_id=None):
    source = str(seed or match_id or "rebirth-bot")
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    return BOT_PERSONALITY_ORDER[int(digest[:2], 16) % len(BOT_PERSONALITY_ORDER)]


def winning_cards(bot_hand, player_card):
    player_attack = card_attack(player_card)
    return [card for card in bot_hand if card_attack(card) > player_attack]


def choose_defensive(bot_hand, player_card):
    candidates = winning_cards(bot_hand, player_card) or list(bot_hand)
    return sorted(candidates, key=lambda card: (card_guard(card), card_attack(card), card["name"]))[-1]


def choose_aggressive(bot_hand, player_card):
    winners = winning_cards(bot_hand, player_card)
    candidates = winners or list(bot_hand)
    return sorted(candidates, key=lambda card: (card_attack(card), ability_priority(card), card_guard(card), card["name"]))[-1]


def choose_opportunist(bot_hand, player_card):
    winners = winning_cards(bot_hand, player_card)
    if winners:
        return sorted(
            winners,
            key=lambda card: (ability_priority(card), -card_attack(card), card_guard(card), card["name"]),
        )[-1]
    return sorted(bot_hand, key=lambda card: (ability_priority(card), card_attack(card), card_guard(card), card["name"]))[-1]


def choose_response(bot_hand, player_card, profile_id=None):
    if not bot_hand:
        return None

    profile_id = normalize_personality(profile_id)
    if profile_id == "aggressive":
        choice = choose_aggressive(bot_hand, player_card)
    elif profile_id == "opportunist":
        choice = choose_opportunist(bot_hand, player_card)
    else:
        choice = choose_defensive(bot_hand, player_card)
    return deepcopy(choice)
