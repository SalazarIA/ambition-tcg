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


def build_card_lore(card):
    name = card.get("name", "Unknown Card")
    element = card.get("element", "Global")
    sigil = card.get("sigil", "Global")
    card_type = card.get("type", "Card")

    element_data = ELEMENT_ARCHETYPES.get(element, ELEMENT_ARCHETYPES["Global"])
    sigil_data = SIGIL_ARCHETYPES.get(sigil, SIGIL_ARCHETYPES["Global"])

    if card_type == "Monster":
        return f"{name} carries {element.lower()} ambition: {element_data['lore_template']}"

    if card_type == "Spell":
        return f"{name} channels a universal tactic for sudden advantage."

    if card_type == "Trap":
        return f"{name} waits for the opponent to overreach."

    return f"{name} belongs to the Ambitionz duel system."


def identity_for_card(card):
    element = card.get("element", "Global")
    sigil = card.get("sigil", "Global")
    card_type = card.get("type", "Card")

    element_data = ELEMENT_ARCHETYPES.get(element, ELEMENT_ARCHETYPES["Global"])
    sigil_data = SIGIL_ARCHETYPES.get(sigil, SIGIL_ARCHETYPES["Global"])

    return {
        "archetype": sigil_data.get("archetype") or element_data.get("archetype"),
        "identity_role": sigil_data.get("identity_role") or element_data.get("identity_role"),
        "lore": build_card_lore(card),
        "tactical_hint": sigil_data.get("tactical_hint") or element_data.get("tactical_hint"),
        "type_identity": CARD_TYPE_IDENTITY.get(card_type, "Flexible card identity."),
    }


def apply_identity_to_catalog(card_catalog):
    for card in card_catalog:
        identity = identity_for_card(card)

        card.setdefault("archetype", identity["archetype"])
        card.setdefault("identity_role", identity["identity_role"])
        card.setdefault("lore", identity["lore"])
        card.setdefault("tactical_hint", identity["tactical_hint"])
        card.setdefault("type_identity", identity["type_identity"])

    return card_catalog
