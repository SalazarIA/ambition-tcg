"""Pure combat math shared by the authoritative engine and bot projections."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple


BREAKTHROUGH_OVERFLOW_CAP = 2


def card_attack(card: Optional[Dict[str, Any]]) -> int:
    card = card or {}
    return max(
        0,
        int(card.get("attack", card.get("power", 0)) or 0)
        + int(card.get("attack_adjustment", 0) or 0),
    )


def card_guard(card: Optional[Dict[str, Any]]) -> int:
    card = card or {}
    return max(
        0,
        int(card.get("guard", 0) or 0)
        + int(card.get("guard_adjustment", 0) or 0),
    )


def ability_key(card: Optional[Dict[str, Any]]) -> str:
    return str((card or {}).get("ability_key") or "").strip()


def synergy_bonuses(
    card: Optional[Dict[str, Any]],
    owner_field: Optional[Iterable[Dict[str, Any]]],
    *,
    owner_hp: int = 30,
) -> Tuple[int, int]:
    if not card or not isinstance(card.get("synergy"), dict):
        return 0, 0
    from services.rebirth_keywords import synergy_active, synergy_bonus

    field = [candidate for candidate in (owner_field or []) if candidate]
    if not synergy_active(card, field, owner_hp=int(owner_hp or 0)):
        return 0, 0
    bonus = synergy_bonus(card)
    return int(bonus.get("attack", 0) or 0), int(bonus.get("guard", 0) or 0)


def ability_attack_bonus(
    card: Dict[str, Any],
    opponent_card: Optional[Dict[str, Any]],
    *,
    turn: int = 1,
) -> Tuple[int, Optional[str]]:
    key = ability_key(card)
    if key == "high_guard" and card_guard(opponent_card) <= 3:
        return 1, f"{card['name']} usou Guarda Alta para +1 de ataque no combate."
    if key == "silent_pursuit" and int(turn or 1) <= 2:
        return 1, f"{card['name']} usou Perseguição Silenciosa para +1 de ataque inicial."
    if key == "fire_surge" and int(turn or 1) <= 2:
        return 2, f"{card['name']} avançou para +2 de ataque inicial."
    if key == "water_tide" and int(turn or 1) >= 3:
        return 2, f"{card['name']} surfou a maré crescente para +2 de ataque."
    if key == "earth_fortify":
        bonus = min(2, max(0, card_guard(card) // 4))
        if bonus:
            return bonus, f"{card['name']} converteu guarda em +{bonus} de ataque."
    return 0, None


def effective_attack(
    card: Dict[str, Any],
    opponent_card: Optional[Dict[str, Any]],
    *,
    turn: int = 1,
    owner_field: Optional[Iterable[Dict[str, Any]]] = None,
    owner_hp: int = 30,
) -> Tuple[int, List[str]]:
    attack = card_attack(card)
    events: List[str] = []
    synergy_attack, _ = synergy_bonuses(card, owner_field, owner_hp=owner_hp)
    if synergy_attack:
        attack += synergy_attack
        events.append(f"{card['name']} ativa sinergia para +{synergy_attack} de ataque.")
    from services.rebirth_keywords import SUNDER_ATTACK_BONUS, sunder_active

    if sunder_active(card, list(owner_field or []), opponent_card):
        attack += SUNDER_ATTACK_BONUS
        events.append(f"{card['name']} ativa Ruptura para +{SUNDER_ATTACK_BONUS} de ataque contra a muralha.")
    ability_bonus, message = ability_attack_bonus(card, opponent_card, turn=turn)
    attack += ability_bonus
    if message:
        events.append(message)
    return attack, events


def tie_priority(card: Dict[str, Any], defender_wounded: bool = False) -> int:
    if ability_key(card) in {"fade_cut", "bleed_mark", "shadow_mark", "fire_execute"} and defender_wounded:
        return 2
    return 0


def overflow_hero_damage(
    attacker: Optional[Dict[str, Any]],
    damage: int,
    defender_guard: int,
) -> int:
    overflow = max(0, int(damage or 0) - max(0, int(defender_guard or 0)))
    if not overflow:
        return 0

    from services.rebirth_keywords import has_keyword

    if has_keyword(attacker or {}, "PIERCE"):
        return overflow
    return min(BREAKTHROUGH_OVERFLOW_CAP, overflow)


def damage_details(
    attacker: Dict[str, Any],
    defender: Dict[str, Any],
    *,
    defender_wounded: bool = False,
    attacker_field: Optional[Iterable[Dict[str, Any]]] = None,
    defender_field: Optional[Iterable[Dict[str, Any]]] = None,
    attacker_hp: int = 30,
    defender_hp: int = 30,
) -> Dict[str, Any]:
    attack_total = card_attack(attacker)
    guard_total = card_guard(defender)
    synergy_attack, _ = synergy_bonuses(attacker, attacker_field, owner_hp=attacker_hp)
    _, synergy_guard = synergy_bonuses(defender, defender_field, owner_hp=defender_hp)
    attack_total += synergy_attack
    guard_total += synergy_guard
    amount = max(1, attack_total - guard_total // 2)
    events: List[str] = []
    attacker_key = ability_key(attacker)
    defender_key = ability_key(defender)

    bonuses = {
        "molten_bite": (1, "adicionou +1 de dano com Molten Bite."),
        "inferno_bite": (3, "adicionou +3 de dano com Inferno Bite."),
        "bleed_mark": (1, "marcou o alvo para +1 de dano."),
        "immovable": (2, "transformou guarda em +2 de contra-dano."),
        "fire_direct": (2, "causou +2 de dano direto de fogo."),
        "shadow_decay": (1, "abriu uma ferida de deterioração para +1 de dano."),
        "shadow_drain": (1, "drenou +1 de dano pelas sombras."),
    }
    if attacker_key == "rending_strike" and defender_wounded:
        amount += 2
        events.append(f"{attacker['name']} explorou a ferida para +2 de dano.")
    elif attacker_key == "apex_rend" and defender_wounded:
        amount += 3
        events.append(f"{attacker['name']} rasgou a ferida antiga para +3 de dano.")
    elif attacker_key == "storm_dive" and card_guard(defender) <= 3:
        amount += 2
        events.append(f"{attacker['name']} atravessou a guarda baixa para +2 de dano.")
    elif attacker_key == "fire_execute" and defender_wounded:
        amount += 2
        events.append(f"{attacker['name']} finalizou o alvo ferido para +2 de dano.")
    elif attacker_key in bonuses:
        bonus, copy = bonuses[attacker_key]
        amount += bonus
        events.append(f"{attacker['name']} {copy}")

    if attacker_key == "fortress_hit":
        before_minimum = amount
        amount = max(3, amount)
        if amount > before_minimum:
            events.append(f"{attacker['name']} garantiu 3 de dano com Fortress Hit.")

    reductions = {
        "brace": 2,
        "immovable": 3,
        "fortress_hit": 4,
        "water_guard": 2,
        "earth_bulwark": 3,
    }
    reduction = reductions.get(defender_key, 0)
    if defender_key in {"bulwark", "earth_counter"} and card_attack(attacker) <= 4:
        reduction = 3
    if reduction:
        before_reduction = amount
        amount = max(1, amount - reduction)
        if amount < before_reduction:
            events.append(f"{defender['name']} reduziu o dano recebido em {before_reduction - amount}.")
    return {"amount": amount, "events": events}
