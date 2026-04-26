from game.balance import DEFAULT_SIGIL, SIGIL_RULES
from game.engine import add_ambition
from game.rules import has_elemental_advantage


def get_card_sigil(card):
    if not card:
        return DEFAULT_SIGIL

    sigil = card.get("sigil") or DEFAULT_SIGIL

    if sigil not in SIGIL_RULES:
        return DEFAULT_SIGIL

    return sigil


def get_sigil_rule(card):
    return SIGIL_RULES[get_card_sigil(card)]


def sigil_matches_intent(player, rule):
    required_intent = rule.get("requires_intent")

    if not required_intent:
        return True

    return player.get("intent", "Strike") == required_intent


def sigil_element_condition_met(card, enemy_card, rule):
    if not card or not enemy_card:
        return not rule.get("requires_element_advantage") and not rule.get("requires_element_disadvantage")

    my_element = card.get("element")
    enemy_element = enemy_card.get("element")

    if rule.get("requires_element_advantage"):
        return has_elemental_advantage(my_element, enemy_element)

    if rule.get("requires_element_disadvantage"):
        return has_elemental_advantage(enemy_element, my_element)

    return True


def calculate_sigil_power_bonus(player, card, enemy_card, logs=None):
    if not card:
        return 0

    rule = get_sigil_rule(card)

    if not sigil_matches_intent(player, rule):
        return 0

    if not sigil_element_condition_met(card, enemy_card, rule):
        return 0

    bonus = int(rule.get("power_bonus", 0))

    if bonus > 0 and logs is not None:
        logs.append(f"{card['name']} activated {get_card_sigil(card)} Sigil: +{bonus} power.")

    return bonus


def calculate_sigil_damage_bonus(player, card, enemy_card, logs=None):
    if not card:
        return 0

    rule = get_sigil_rule(card)

    if not sigil_matches_intent(player, rule):
        return 0

    if not sigil_element_condition_met(card, enemy_card, rule):
        return 0

    bonus = int(rule.get("damage_bonus", 0))

    if bonus > 0 and logs is not None:
        logs.append(f"{card['name']} activated {get_card_sigil(card)} Sigil: +{bonus} damage.")

    return bonus


def calculate_sigil_damage_reduction(player, card, enemy_card, damage, logs=None):
    if not card or damage <= 0:
        return 0

    rule = get_sigil_rule(card)

    if not sigil_matches_intent(player, rule):
        return 0

    if not sigil_element_condition_met(card, enemy_card, rule):
        return 0

    reduction = min(int(rule.get("damage_reduction", 0)), damage)

    if reduction > 0 and logs is not None:
        logs.append(f"{card['name']} activated {get_card_sigil(card)} Sigil: blocked {reduction} damage.")

    return reduction


def apply_sigil_ambition_bonus(player, card, enemy_card, logs=None):
    if not card:
        return

    rule = get_sigil_rule(card)

    if not sigil_matches_intent(player, rule):
        return

    if not sigil_element_condition_met(card, enemy_card, rule):
        return

    bonus = int(rule.get("ambition_bonus", 0))

    if bonus > 0:
        add_ambition(player, bonus, f"{get_card_sigil(card)} Sigil alignment", logs)
