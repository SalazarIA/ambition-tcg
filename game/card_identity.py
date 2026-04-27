CARD_IDENTITY_VERSION = "Ambitionz V1.06 Card Identity Pack"

ELEMENT_IDENTITIES = {
    "Fire": {
        "fantasy": "pressure, burst, ambition and aggressive tempo",
        "mechanical_focus": "damage spikes, attack pressure, Overreach payoff",
        "naming_style": "volcanic, solar, furious, royal, explosive",
        "sample_lore": "Fire cards are born from players who choose action before certainty.",
    },
    "Water": {
        "fantasy": "adaptation, flow, patience and tactical recovery",
        "mechanical_focus": "healing, draw smoothing, flexible defense, tempo reset",
        "naming_style": "tide, mirror, abyss, rain, moon, current",
        "sample_lore": "Water cards reward players who bend without breaking.",
    },
    "Earth": {
        "fantasy": "endurance, structure, protection and inevitability",
        "mechanical_focus": "guard value, durability, stable board presence, comeback defense",
        "naming_style": "stone, iron, mountain, root, fortress, relic",
        "sample_lore": "Earth cards turn patience into pressure.",
    },
    "Plant": {
        "fantasy": "growth, synergy, sustain and delayed advantage",
        "mechanical_focus": "combo growth, healing, board cohesion, scaling rewards",
        "naming_style": "bloom, thorn, seed, grove, vine, ancient forest",
        "sample_lore": "Plant cards are weakest alone and dangerous together.",
    },
    "Global": {
        "fantasy": "neutral ambition, utility and universal tactics",
        "mechanical_focus": "flexible tools, low complexity support, tutorial-friendly cards",
        "naming_style": "oath, pact, emblem, tactic, signal, ambition",
        "sample_lore": "Global cards carry the rules of Ambitionz itself.",
    },
}

ARCHETYPES = {
    "Blaze Rush": {
        "elements": ["Fire"],
        "sigils": ["Fury"],
        "style": "fast pressure and decisive Overreach turns",
        "risk": "runs out of stability if the first attack fails",
    },
    "Stonewall Resolve": {
        "elements": ["Earth"],
        "sigils": ["Resolve"],
        "style": "survive pressure, punish reckless attacks, win late",
        "risk": "can be too slow against resource engines",
    },
    "Tide Insight": {
        "elements": ["Water"],
        "sigils": ["Insight"],
        "style": "draw, adapt, read the opponent and choose perfect timing",
        "risk": "needs decisions to matter; weak if effects are too passive",
    },
    "Thorn Harmony": {
        "elements": ["Plant"],
        "sigils": ["Harmony"],
        "style": "grow board synergy and convert sustain into pressure",
        "risk": "falls behind if key pieces are removed early",
    },
    "Ruin Breaker": {
        "elements": ["Fire", "Earth", "Global"],
        "sigils": ["Ruin"],
        "style": "deny opponent plans, punish overextension and force bad trades",
        "risk": "can feel frustrating if disruption is not clearly explained",
    },
}

SIGIL_CARD_DIRECTIONS = {
    "Fury": {
        "effect_direction": "bonus damage, tempo pressure, Strike/Overreach payoff",
        "ideal_text_length": "short",
        "avoid": "complex conditional chains",
    },
    "Resolve": {
        "effect_direction": "damage reduction, Guard payoff, comeback triggers",
        "ideal_text_length": "short to medium",
        "avoid": "stall loops with no end condition",
    },
    "Insight": {
        "effect_direction": "draw, preview, hand smoothing, Focus payoff",
        "ideal_text_length": "medium",
        "avoid": "too much hidden information for new players",
    },
    "Ruin": {
        "effect_direction": "destroy, weaken, tax, punish Overreach or exposed fields",
        "ideal_text_length": "medium",
        "avoid": "unreadable hard control",
    },
    "Harmony": {
        "effect_direction": "heal, buff allies, scale when cards share element or Sigil",
        "ideal_text_length": "short to medium",
        "avoid": "passive effects that do not change decisions",
    },
    "Global": {
        "effect_direction": "basic utility, tutorial cards, flexible support",
        "ideal_text_length": "short",
        "avoid": "stealing identity from specialized Sigils",
    },
}

CARD_WRITING_RULES = [
    "Every card needs a tactical purpose.",
    "Every card name should suggest element, Sigil or role.",
    "Effects should be readable in one quick glance.",
    "Lore should be short: one sentence maximum for beta.",
    "Avoid effects that require reading five other cards to understand.",
    "Starter deck cards must teach the game before they impress the expert.",
]

BETA_DECK_GOALS = [
    "30 cards fixed for testing.",
    "At least one clear aggressive line.",
    "At least one defensive comeback line.",
    "At least one draw/planning line.",
    "At least one synergy/combo line.",
    "Overreach should be tempting but not automatic.",
]
