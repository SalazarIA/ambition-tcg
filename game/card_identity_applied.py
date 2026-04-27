ELEMENT_ARCHETYPES = {
    "Fire": {
        "archetype": "Blaze Rush",
        "identity_role": "Pressure",
        "lore_template": "Born from ambition before certainty.",
        "tactical_hint": "Use to force tempo and punish hesitation.",
    },
    "Water": {
        "archetype": "Tide Insight",
        "identity_role": "Planning",
        "lore_template": "Shaped by patience, flow and perfect timing.",
        "tactical_hint": "Use to adapt, smooth decisions and outread the opponent.",
    },
    "Earth": {
        "archetype": "Stonewall Resolve",
        "identity_role": "Defense",
        "lore_template": "Forged to endure pressure until the enemy overextends.",
        "tactical_hint": "Use to survive, stabilize and punish reckless attacks.",
    },
    "Plant": {
        "archetype": "Thorn Harmony",
        "identity_role": "Synergy",
        "lore_template": "Weak alone, dangerous when the board grows together.",
        "tactical_hint": "Use to build board cohesion and delayed advantage.",
    },
    "Global": {
        "archetype": "Ambition Core",
        "identity_role": "Utility",
        "lore_template": "A neutral tactic carried by every duelist.",
        "tactical_hint": "Use as flexible support for any deck plan.",
    },
}


SIGIL_ARCHETYPES = {
    "Fury": {
        "archetype": "Blaze Rush",
        "identity_role": "Burst",
        "tactical_hint": "Rewards Strike pressure and decisive Overreach turns.",
    },
    "Resolve": {
        "archetype": "Stonewall Resolve",
        "identity_role": "Comeback",
        "tactical_hint": "Rewards Guard timing, survival and late stabilization.",
    },
    "Insight": {
        "archetype": "Tide Insight",
        "identity_role": "Control",
        "tactical_hint": "Rewards Focus, planning and information advantage.",
    },
    "Ruin": {
        "archetype": "Ruin Breaker",
        "identity_role": "Disruption",
        "tactical_hint": "Rewards punishment, denial and breaking opponent plans.",
    },
    "Harmony": {
        "archetype": "Thorn Harmony",
        "identity_role": "Synergy",
        "tactical_hint": "Rewards shared element/Sigil lines and board cohesion.",
    },
    "Global": {
        "archetype": "Ambition Core",
        "identity_role": "Utility",
        "tactical_hint": "Supports simple, readable tactical decisions.",
    },
}


CARD_TYPE_IDENTITY = {
    "Monster": "Board presence and direct duel pressure.",
    "Spell": "Immediate tactical swing.",
    "Trap": "Hidden interaction and defensive counterplay.",
}


def normalized(value, fallback="Global"):
    value = str(value or fallback).strip()
    return value if value else fallback


def build_card_lore(card):
    name = card.get("name", "Unknown Card")
    element = normalized(card.get("element"))
    card_type = normalized(card.get("type"), "Card")

    element_data = ELEMENT_ARCHETYPES.get(element, ELEMENT_ARCHETYPES["Global"])

    if card_type == "Monster":
        return f"{name} carries {element.lower()} ambition: {element_data['lore_template']}"

    if card_type == "Spell":
        return f"{name} channels a universal tactic for sudden advantage."

    if card_type == "Trap":
        return f"{name} waits for the opponent to overreach."

    return f"{name} belongs to the Ambitionz duel system."


def identity_for_card(card):
    element = normalized(card.get("element"))
    sigil = normalized(card.get("sigil"))
    card_type = normalized(card.get("type"), "Card")

    element_data = ELEMENT_ARCHETYPES.get(element, ELEMENT_ARCHETYPES["Global"])
    sigil_data = SIGIL_ARCHETYPES.get(sigil)

    # Regra principal:
    # - Sigil é a personalidade dominante da carta.
    # - Elemento define fantasia/lore e fallback.
    # - Magias/armadilhas Global/Global ficam como Ambition Core.
    if sigil_data:
        archetype = sigil_data["archetype"]
        identity_role = sigil_data["identity_role"]
        tactical_hint = sigil_data["tactical_hint"]
    else:
        archetype = element_data["archetype"]
        identity_role = element_data["identity_role"]
        tactical_hint = element_data["tactical_hint"]

    return {
        "archetype": archetype,
        "identity_role": identity_role,
        "lore": build_card_lore(card),
        "tactical_hint": tactical_hint,
        "type_identity": CARD_TYPE_IDENTITY.get(card_type, "Flexible card identity."),
    }


def apply_identity_to_catalog(card_catalog):
    for card in card_catalog:
        identity = identity_for_card(card)

        card["archetype"] = identity["archetype"]
        card["identity_role"] = identity["identity_role"]
        card["lore"] = identity["lore"]
        card["tactical_hint"] = identity["tactical_hint"]
        card["type_identity"] = identity["type_identity"]

    return card_catalog
