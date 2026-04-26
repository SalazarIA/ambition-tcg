from game.balance import (
    AMBITION_MAX,
    AMBITION_UNLEASH_COST,
    AMBITION_UNLEASH_POWER_BONUS,
    OVERREACH_PENALTY_DAMAGE,
    OVERREACH_RESET_VALUE,
)


def clamp_ambition(player):
    player["ambition"] = max(0, min(int(player.get("ambition", 0)), AMBITION_MAX))


def add_ambition(player, amount, reason, logs=None):
    if not player:
        return

    amount = int(amount)

    if amount <= 0:
        return

    player["ambition"] = int(player.get("ambition", 0)) + amount

    if logs is not None:
        logs.append(f"{player['name']} gained +{amount} Ambition: {reason}.")

    if player["ambition"] > AMBITION_MAX:
        trigger_overreach(player, logs)
    else:
        clamp_ambition(player)


def spend_ambition(player, amount):
    amount = int(amount)

    if int(player.get("ambition", 0)) < amount:
        return False

    player["ambition"] -= amount
    clamp_ambition(player)
    return True


def can_unleash_ambition(player):
    return int(player.get("ambition", 0)) >= AMBITION_UNLEASH_COST and bool(player.get("field_m"))


def request_unleash(player):
    if can_unleash_ambition(player):
        player["wants_unleash"] = True
        return True

    player["wants_unleash"] = False
    return False


def cancel_unleash(player):
    player["wants_unleash"] = False


def resolve_manual_unleash(player, logs=None):
    if not player.get("wants_unleash"):
        return 0

    if not can_unleash_ambition(player):
        player["wants_unleash"] = False
        return 0

    if player.get("ambition_unleashed"):
        return 0

    spend_ambition(player, AMBITION_UNLEASH_COST)

    player["ambition_unleashed"] = True
    player["wants_unleash"] = False

    if logs is not None:
        logs.append(
            f"{player['name']} unleashed Ambition manually: {player['field_m']['name']} gains +{AMBITION_UNLEASH_POWER_BONUS} power this battle."
        )

    return AMBITION_UNLEASH_POWER_BONUS


def trigger_overreach(player, logs=None):
    player["ambition"] = OVERREACH_RESET_VALUE
    player["hp"] -= OVERREACH_PENALTY_DAMAGE
    player["overreach_count"] = int(player.get("overreach_count", 0)) + 1

    if logs is not None:
        logs.append(
            f"{player['name']} suffered Overreach: Ambition overflow dealt {OVERREACH_PENALTY_DAMAGE} damage and reset Ambition to {OVERREACH_RESET_VALUE}."
        )


def card_generates_ambition(card):
    gain = 0
    reasons = []

    if not card:
        return gain, reasons

    card_type = card.get("type")
    cost = int(card.get("cost", 1))
    effect = card.get("effect", "None")

    if card_type == "Monster":
        gain += 1
        reasons.append("played a monster")

    if cost >= 3:
        gain += 1
        reasons.append("played a high-cost card")

    if effect in ["Burn", "Drain", "BurnOnSummon", "Piercing"]:
        gain += 1
        reasons.append("used an aggressive effect")

    return gain, reasons


def register_card_played_for_ambition(player, card, logs=None):
    gain, reasons = card_generates_ambition(card)

    if gain <= 0:
        return

    reason = ", ".join(reasons)
    add_ambition(player, gain, reason, logs)
