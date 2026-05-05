from game.deck import draw_card
from game.balance import (
    ELEMENT_ADVANTAGE_POWER_BONUS,
    MAX_ENERGY,
)


MAX_HP = 5000
ELEMENTAL_BONUS = ELEMENT_ADVANTAGE_POWER_BONUS


ELEMENT_ADVANTAGES = {
    "Fire": "Plant",
    "Plant": "Earth",
    "Earth": "Water",
    "Water": "Fire",
}


def energy_for_round(round_number):
    return min(MAX_ENERGY, max(2, int(round_number) + 1))


def reset_player_energy(player, round_number):
    max_energy = energy_for_round(round_number)
    player["max_energy"] = max_energy
    player["energy"] = max_energy


def can_pay_cost(player, card):
    cost = int(card.get("cost", 1))
    return int(player.get("energy", 0)) >= cost


def pay_card_cost(player, card):
    cost = int(card.get("cost", 1))

    if not can_pay_cost(player, card):
        return False

    player["energy"] -= cost
    return True


def has_elemental_advantage(attacker_element, defender_element):
    return ELEMENT_ADVANTAGES.get(attacker_element) == defender_element


def calculate_final_power(attacker, defender):
    base_power = int(attacker.get("power", 0))
    bonus = 0

    if has_elemental_advantage(attacker.get("element"), defender.get("element")):
        bonus = ELEMENTAL_BONUS

    return base_power + bonus


def elemental_log(attacker, defender, owner_name):
    if not attacker or not defender:
        return None

    attacker_element = attacker.get("element")
    defender_element = defender.get("element")

    if has_elemental_advantage(attacker_element, defender_element):
        return f"{owner_name}'s {attacker_element} monster has elemental advantage over {defender_element}: +{ELEMENTAL_BONUS} power."

    return None


def apply_damage(player, damage):
    damage = max(0, int(damage))
    shield = int(player.get("shield", 0))

    if shield > 0:
        blocked = min(shield, damage)
        damage -= blocked
        player["shield"] -= blocked

    player["hp"] -= damage

    return damage


def heal_player(player, amount):
    player["hp"] += int(amount)

    if player["hp"] > MAX_HP:
        player["hp"] = MAX_HP


def weaken_enemy_monster(enemy, amount):
    if enemy.get("field_m"):
        enemy["field_m"]["power"] = max(0, int(enemy["field_m"]["power"]) - int(amount))
        return True

    return False


def boost_own_monster(player, amount):
    if player.get("field_m"):
        player["field_m"]["power"] += int(amount)
        return True

    return False


def apply_summon_effect(player, enemy, card):
    logs = []

    if not card:
        return logs

    effect = card.get("effect")
    value = int(card.get("value", 0))

    if effect == "None":
        return logs

    if effect == "HealOnSummon":
        heal_player(player, value)
        logs.append(f"{player['name']}'s {card['name']} restored {value} HP when summoned.")

    elif effect == "BurnOnSummon":
        final_damage = apply_damage(enemy, value)
        logs.append(f"{player['name']}'s {card['name']} dealt {final_damage} summon burn damage.")

    elif effect == "DrawOnSummon":
        drawn = 0

        for _ in range(value):
            card_drawn = draw_card(player)

            if card_drawn:
                drawn += 1

        logs.append(f"{player['name']}'s {card['name']} drew {drawn} card(s) when summoned.")

    elif effect == "ShieldOnSummon":
        player["shield"] += value
        logs.append(f"{player['name']}'s {card['name']} created {value} shield.")

    elif effect == "BoostSelf":
        card["power"] += value
        logs.append(f"{player['name']}'s {card['name']} gained {value} power.")

    elif effect == "WeakenEnemy":
        success = weaken_enemy_monster(enemy, value)

        if success:
            logs.append(f"{player['name']}'s {card['name']} weakened the enemy monster by {value}.")
        else:
            logs.append(f"{player['name']}'s {card['name']} tried to weaken, but there was no enemy monster.")

    elif effect == "Piercing":
        logs.append(f"{player['name']}'s {card['name']} has Piercing. If it wins combat, it deals extra damage.")

    else:
        logs.append(f"{player['name']}'s {card['name']} has an unknown effect.")

    return logs


def apply_spell(player, enemy, spell):
    effect = spell.get("effect")
    value = int(spell.get("value", 0))

    logs = []

    if effect == "Heal":
        heal_player(player, value)
        logs.append(f"{player['name']} cast {spell['name']} and restored {value} HP.")

    elif effect == "Drain":
        final_damage = apply_damage(enemy, value)
        heal_player(player, final_damage)
        logs.append(f"{player['name']} cast {spell['name']}, drained {final_damage} HP and healed for the same amount.")

    elif effect == "Boost":
        success = boost_own_monster(player, value)

        if success:
            logs.append(f"{player['name']} cast {spell['name']} and boosted their monster by {value}.")
        else:
            logs.append(f"{player['name']} cast {spell['name']}, but had no monster to boost.")

    elif effect == "Draw":
        drawn = 0

        for _ in range(value):
            card_drawn = draw_card(player)

            if card_drawn:
                drawn += 1

        logs.append(f"{player['name']} cast {spell['name']} and drew {drawn} card(s).")

    elif effect == "Shield":
        player["shield"] += value
        logs.append(f"{player['name']} cast {spell['name']} and gained {value} shield.")

    elif effect == "Burn":
        final_damage = apply_damage(enemy, value)
        logs.append(f"{player['name']} cast {spell['name']} and dealt {final_damage} burn damage.")

    elif effect == "Weaken":
        success = weaken_enemy_monster(enemy, value)

        if success:
            logs.append(f"{player['name']} cast {spell['name']} and weakened the enemy monster by {value}.")
        else:
            logs.append(f"{player['name']} cast {spell['name']}, but there was no enemy monster.")

    else:
        logs.append(f"{player['name']} cast {spell['name']}, but nothing happened.")

    return logs


def apply_trap(player, enemy, trap):
    effect = trap.get("effect")
    value = int(trap.get("value", 0))

    logs = []

    if effect == "Counter":
        final_damage = apply_damage(enemy, value)
        logs.append(f"{player['name']}'s trap {trap['name']} dealt {final_damage} counter damage.")

    elif effect == "Weaken":
        success = weaken_enemy_monster(enemy, value)

        if success:
            logs.append(f"{player['name']}'s trap {trap['name']} weakened the enemy monster by {value}.")
        else:
            logs.append(f"{player['name']}'s trap {trap['name']} found no target.")

    elif effect == "Shield":
        player["shield"] += value
        logs.append(f"{player['name']}'s trap {trap['name']} created {value} shield.")

    elif effect == "Burn":
        final_damage = apply_damage(enemy, value)
        logs.append(f"{player['name']}'s trap {trap['name']} dealt {final_damage} burn damage.")

    elif effect == "Heal":
        heal_player(player, value)
        logs.append(f"{player['name']}'s trap {trap['name']} restored {value} HP.")

    else:
        logs.append(f"{player['name']}'s trap {trap['name']} had no effect.")

    return logs


def piercing_bonus_damage(card):
    if not card:
        return 0

    if card.get("effect") == "Piercing":
        return int(card.get("value", 0))

    return 0
