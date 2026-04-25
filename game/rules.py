from game.deck import draw_card


ELEMENT_ADVANTAGES = {
    "Water": "Fire",
    "Fire": "Plant",
    "Plant": "Earth",
    "Earth": "Water",
}


def has_elemental_advantage(attacker_element, defender_element):
    return ELEMENT_ADVANTAGES.get(attacker_element) == defender_element


def calculate_final_power(attacker, defender):
    base_power = int(attacker.get("power", 0))
    bonus = 0

    if has_elemental_advantage(attacker.get("element"), defender.get("element")):
        bonus = 300

    return base_power + bonus


def apply_damage(player, damage):
    shield = int(player.get("shield", 0))

    if shield > 0:
        blocked = min(shield, damage)
        damage -= blocked
        player["shield"] -= blocked

    player["hp"] -= damage

    return damage


def heal_player(player, amount):
    player["hp"] += amount

    if player["hp"] > 5000:
        player["hp"] = 5000


def weaken_enemy_monster(enemy, amount):
    if enemy.get("field_m"):
        enemy["field_m"]["power"] = max(0, enemy["field_m"]["power"] - amount)
        return True

    return False


def boost_own_monster(player, amount):
    if player.get("field_m"):
        player["field_m"]["power"] += amount
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
        logs.append(f"{player['name']} summoned {card['name']} and recovered {value} HP.")

    elif effect == "BurnOnSummon":
        final_damage = apply_damage(enemy, value)
        logs.append(f"{player['name']} summoned {card['name']} and dealt {final_damage} burn damage.")

    elif effect == "DrawOnSummon":
        drawn = 0

        for _ in range(value):
            card_drawn = draw_card(player)

            if card_drawn:
                drawn += 1

        logs.append(f"{player['name']} summoned {card['name']} and drew {drawn} card(s).")

    elif effect == "ShieldOnSummon":
        player["shield"] += value
        logs.append(f"{player['name']} summoned {card['name']} and gained {value} shield.")

    elif effect == "BoostSelf":
        card["power"] += value
        logs.append(f"{player['name']} summoned {card['name']} and gained {value} power.")

    elif effect == "WeakenEnemy":
        success = weaken_enemy_monster(enemy, value)

        if success:
            logs.append(f"{player['name']} summoned {card['name']} and weakened the enemy monster by {value}.")
        else:
            logs.append(f"{player['name']} summoned {card['name']}, but there was no enemy monster to weaken.")

    elif effect == "Piercing":
        logs.append(f"{player['name']} summoned {card['name']} with piercing energy.")

    else:
        logs.append(f"{player['name']} summoned {card['name']}, but its effect is unknown.")

    return logs


def apply_spell(player, enemy, spell):
    effect = spell.get("effect")
    value = int(spell.get("value", 0))

    logs = []

    if effect == "Heal":
        heal_player(player, value)
        logs.append(f"{player['name']} used {spell['name']} and recovered {value} HP.")

    elif effect == "Drain":
        final_damage = apply_damage(enemy, value)
        heal_player(player, final_damage)
        logs.append(f"{player['name']} used {spell['name']} and drained {final_damage} HP.")

    elif effect == "Boost":
        success = boost_own_monster(player, value)

        if success:
            logs.append(f"{player['name']} used {spell['name']} and boosted their monster by {value}.")
        else:
            logs.append(f"{player['name']} used {spell['name']}, but had no monster to boost.")

    elif effect == "Draw":
        drawn = 0

        for _ in range(value):
            card_drawn = draw_card(player)

            if card_drawn:
                drawn += 1

        logs.append(f"{player['name']} used {spell['name']} and drew {drawn} card(s).")

    elif effect == "Shield":
        player["shield"] += value
        logs.append(f"{player['name']} used {spell['name']} and gained {value} shield.")

    elif effect == "Burn":
        final_damage = apply_damage(enemy, value)
        logs.append(f"{player['name']} used {spell['name']} and dealt {final_damage} burn damage.")

    elif effect == "Weaken":
        success = weaken_enemy_monster(enemy, value)

        if success:
            logs.append(f"{player['name']} used {spell['name']} and weakened the enemy monster by {value}.")
        else:
            logs.append(f"{player['name']} used {spell['name']}, but there was no enemy monster.")

    else:
        logs.append(f"{player['name']} used {spell['name']}, but nothing happened.")

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
            logs.append(f"{player['name']}'s trap {trap['name']} weakened enemy monster by {value}.")
        else:
            logs.append(f"{player['name']}'s trap {trap['name']} found no target.")

    elif effect == "Shield":
        player["shield"] += value
        logs.append(f"{player['name']}'s trap {trap['name']} created a shield of {value}.")

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