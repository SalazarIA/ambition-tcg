"""Ascension-native taxonomy and presentation helpers."""

from __future__ import annotations

from collections import Counter


ASCENSION_TYPE_LABELS = {
    "champion": "Champion",
    "technique": "Technique",
    "relic": "Relic",
    "scheme": "Scheme",
    "ascension": "Ascension",
}

LEGACY_TYPE_MAP = {
    "monster": "champion",
    "creature": "champion",
    "unit": "champion",
    "spell": "technique",
    "magic": "technique",
    "artifact": "relic",
    "equipment": "relic",
    "trap": "scheme",
    "ultimate": "ascension",
}


def normalize_ascension_type(value):
    key = str(value or "").strip().lower()
    return ASCENSION_TYPE_LABELS.get(key) and key or LEGACY_TYPE_MAP.get(key, key)


def ascension_type_label(value):
    key = normalize_ascension_type(value)
    return ASCENSION_TYPE_LABELS.get(key, "Technique")


def card_strategy_role(card):
    card_type = normalize_ascension_type(card.get("type"))
    resolve = card.get("resolve") or {}
    if card_type == "champion":
        pressure = int(resolve.get("pressure") or 0)
        guard = int(resolve.get("guard") or 0)
        if pressure > guard + 1:
            return "Pressure Champion"
        if guard > pressure:
            return "Anchor Champion"
        return "Balanced Champion"
    if card_type == "technique":
        if resolve.get("damage"):
            return "Direct Pressure"
        if resolve.get("draw") or resolve.get("ambition"):
            return "Momentum Technique"
        return "Tactical Technique"
    if card_type == "relic":
        return "Persistent Modifier"
    if card_type == "scheme":
        return "Prepared Mind Game"
    if card_type == "ascension":
        return "Finisher Pressure"
    return "Flexible Tactic"


def card_strategy_scores(card):
    card_type = normalize_ascension_type(card.get("type"))
    resolve = card.get("resolve") or {}
    pressure = int(resolve.get("pressure") or 0) + int(resolve.get("damage") or 0)
    control = int(resolve.get("guard") or 0) + (2 if card_type in {"scheme", "relic"} else 0)
    momentum = int(resolve.get("ambition") or 0) + int(resolve.get("draw") or 0) + int(resolve.get("burn_ambition") or 0)

    if card_type == "champion":
        soul_bonus = resolve.get("soul_bonus") or {}
        for bonus in soul_bonus.values():
            pressure += int(bonus.get("pressure") or 0)
            control += int(bonus.get("guard") or 0) + int(bonus.get("heal") or 0)
            momentum += int(bonus.get("ambition") or 0) + int(bonus.get("draw") or 0)
    if card_type == "relic":
        for bonus in (resolve.get("intent_bonus") or {}).values():
            pressure += int(bonus.get("pressure") or 0)
            control += int(bonus.get("guard") or 0) + int(bonus.get("heal") or 0)
            momentum += int(bonus.get("ambition") or 0) + int(bonus.get("draw") or 0)

    return {
        "pressure": max(0, pressure),
        "control": max(0, control),
        "momentum": max(0, momentum),
    }


def enrich_ascension_card(card, owned_ids=None, new_ids=None):
    owned_ids = set(owned_ids or [])
    new_ids = set(new_ids or [])
    enriched = dict(card)
    enriched["type_key"] = normalize_ascension_type(card.get("type"))
    enriched["type_label"] = ascension_type_label(card.get("type"))
    enriched["role"] = card_strategy_role(card)
    enriched["strategy"] = card_strategy_scores(card)
    enriched["owned"] = card.get("id") in owned_ids if owned_ids else True
    enriched["locked"] = not enriched["owned"]
    enriched["is_new"] = card.get("id") in new_ids
    return enriched


def ascension_deck_summary(deck):
    cards = list(deck or [])
    counts = Counter(normalize_ascension_type(card.get("type")) for card in cards)
    totals = {"pressure": 0, "control": 0, "momentum": 0}
    for card in cards:
        scores = card_strategy_scores(card)
        for key in totals:
            totals[key] += scores[key]

    if not cards:
        posture = "Empty"
    elif totals["pressure"] >= totals["control"] + 5 and totals["pressure"] >= totals["momentum"]:
        posture = "Pressure-led"
    elif totals["control"] >= totals["pressure"] and totals["control"] >= totals["momentum"]:
        posture = "Control-led"
    elif totals["momentum"] >= totals["pressure"]:
        posture = "Momentum-led"
    else:
        posture = "Balanced"

    return {
        "total": len(cards),
        "counts": {key: counts.get(key, 0) for key in ASCENSION_TYPE_LABELS},
        "labels": ASCENSION_TYPE_LABELS,
        "strategy": totals,
        "posture": posture,
    }
