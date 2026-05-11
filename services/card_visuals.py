"""Deterministic card visual profiles for arena rendering.

The real image pipeline can swap these art URLs for generated or illustrated
assets later without changing the arena_state_v50 contract.
"""

from __future__ import annotations

import re
from typing import Any, Dict


ELEMENT_PALETTES: Dict[str, Dict[str, str]] = {
    "fire": {"primary": "#d8482f", "secondary": "#f7a94d", "accent": "#ffe2a3"},
    "water": {"primary": "#2588c7", "secondary": "#62dddf", "accent": "#d8fbff"},
    "earth": {"primary": "#6d7950", "secondary": "#c8aa64", "accent": "#f2ddb0"},
    "plant": {"primary": "#318b57", "secondary": "#9bd865", "accent": "#e1ffd1"},
    "global": {"primary": "#8c78d8", "secondary": "#d4b56d", "accent": "#fff2c2"},
    "neutral": {"primary": "#677182", "secondary": "#c6cfdd", "accent": "#f4f7ff"},
}

RARITY_FRAMES = {
    "common": "iron",
    "uncommon": "verdant",
    "rare": "arcane",
    "ultra_rare": "mythic",
    "unique": "signature",
    "beta": "prototype",
}


def slug(value: Any, fallback: str = "neutral") -> str:
    text = str(value or fallback).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text or fallback


def element_key(card: Dict[str, Any]) -> str:
    element = slug(card.get("element"), "neutral")
    return element if element in ELEMENT_PALETTES else "neutral"


def rarity_key(card: Dict[str, Any]) -> str:
    rarity = slug(card.get("rarity"), "common")
    return rarity or "common"


def card_visual_profile(card: Dict[str, Any]) -> Dict[str, Any]:
    element = element_key(card)
    rarity = rarity_key(card)
    kind = slug(card.get("kind") or card.get("type"), "card")
    faction = element
    card_id = slug(card.get("id") or card.get("name"), "card")
    frame_key = f"{RARITY_FRAMES.get(rarity, rarity)}_{faction}"
    image = str(card.get("image") or "").strip().lstrip("/")
    art_url = f"/static/img/{image}" if image and "placeholder" not in image else f"/static/img/cards/elemental/{element}.svg"

    impact = "arcane"
    if int(card.get("damage") or 0) > 0:
        impact = "impact"
    elif int(card.get("shield") or 0) > 0:
        impact = "shield"
    elif kind == "creature":
        impact = "summon"
    elif kind == "support":
        impact = "aura"

    return {
        "faction": faction,
        "frame_key": frame_key,
        "rarity_frame": RARITY_FRAMES.get(rarity, rarity),
        "art_key": f"{faction}_{kind}_{card_id}",
        "art_style": "elemental_painted",
        "art_url": art_url,
        "palette": ELEMENT_PALETTES[element],
        "vfx": {
            "cast": f"{faction}_cast",
            "impact": f"{faction}_{impact}",
            "trail": f"{faction}_trail",
        },
        "sfx": {
            "cast": "cardFly",
            "impact": "cardImpact" if impact != "shield" else "shield",
            "resolve": "roundResolve",
        },
        "animation": {
            "enter": "card_summon" if kind == "creature" else "card_cast",
            "resolve": impact,
            "duration_ms": 420,
        },
        "illustration_prompt": (
            f"Premium fantasy trading card art, {faction} faction, {kind}, "
            f"{card.get('name') or card_id}, crisp silhouette, collectible card finish"
        ),
    }
