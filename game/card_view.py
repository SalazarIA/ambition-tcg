from game.card_sets import enrich_card_runtime
from game.balance import SIGIL_RULES


SIGIL_COLORS = {
    "Fury": "sigil-fury",
    "Resolve": "sigil-resolve",
    "Insight": "sigil-insight",
    "Ruin": "sigil-ruin",
    "Harmony": "sigil-harmony",
    "Global": "sigil-global",
}

ROLE_COLORS = {
    "Aggressor": "role-aggressor",
    "Defender": "role-defender",
    "Controller": "role-controller",
    "Balancer": "role-balancer",
    "Finisher": "role-finisher",
}


def card_sigil(card):
    return card.get("sigil", "Global")


def card_role(card):
    return card.get("role", "Balancer")


def sigil_css_class(card):
    return SIGIL_COLORS.get(card_sigil(card), "sigil-global")


def role_css_class(card):
    return ROLE_COLORS.get(card_role(card), "role-balancer")


def sigil_description(card):
    sigil = card_sigil(card)
    return SIGIL_RULES.get(sigil, {}).get("description", "No Sigil effect.")


def enrich_card_for_view(card):
    copy = dict(card)

    copy["sigil"] = card_sigil(copy)
    copy["role"] = card_role(copy)
    copy["sigil_css"] = sigil_css_class(copy)
    copy["role_css"] = role_css_class(copy)
    copy["sigil_description"] = sigil_description(copy)

    return copy


def enrich_cards_for_view(cards):
    return [enrich_card_for_view(card) for card in cards]



def enrich_cards_for_game_view(cards):
    """Runtime-safe card view used by new UI layers."""
    return [
        enrich_card_runtime(card, index=index)
        for index, card in enumerate(cards or [])
    ]
