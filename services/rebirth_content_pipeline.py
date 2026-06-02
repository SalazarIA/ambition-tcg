"""Content and art validation pipeline for the Rebirth card set."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from services.rebirth_cards import PLAYER_DECK, catalog_payload, validate_deck_distribution


CONTENT_PIPELINE_VERSION = "content-pipeline-v1"
REQUIRED_FIELDS = ("id", "name", "type", "rarity", "cost", "ability_name", "ability_text")
TEXT_LIMITS = {"name": 34, "ability_name": 34, "ability_text": 132}


def _root(root_path: Optional[str] = None) -> Path:
    if root_path:
        return Path(root_path)
    return Path(__file__).resolve().parents[1]


def _asset_exists(root: Path, art: str) -> bool:
    if not art:
        return False
    if art.startswith("http://") or art.startswith("https://"):
        return True
    return (root / art.lstrip("/")).exists()


def _iter_errors(cards: Iterable[Dict[str, Any]], root: Path) -> Iterable[Dict[str, Any]]:
    seen = set()
    for card in cards:
        card_id = str(card.get("id") or "")
        if not card_id:
            yield {"severity": "error", "card_id": card_id, "code": "missing_id", "message": "Card without id."}
            continue
        if card_id in seen:
            yield {"severity": "error", "card_id": card_id, "code": "duplicate_id", "message": "Duplicate card id."}
        seen.add(card_id)
        for field in REQUIRED_FIELDS:
            if card.get(field) in (None, ""):
                yield {"severity": "error", "card_id": card_id, "code": "missing_field", "message": f"Missing {field}."}
        for field, limit in TEXT_LIMITS.items():
            value = str(card.get(field) or "")
            if len(value) > limit:
                yield {
                    "severity": "warning",
                    "card_id": card_id,
                    "code": "text_over_budget",
                    "message": f"{field} has {len(value)} chars; budget is {limit}.",
                }
        if "built-in method" in str(card):
            yield {"severity": "error", "card_id": card_id, "code": "template_leak", "message": "Template method leak in card payload."}
        if not _asset_exists(root, str(card.get("art") or "")):
            yield {"severity": "warning", "card_id": card_id, "code": "missing_art_asset", "message": "Art asset is missing or not committed."}


def content_pipeline_report(*, root_path: Optional[str] = None) -> Dict[str, Any]:
    root = _root(root_path)
    cards = catalog_payload()
    findings: List[Dict[str, Any]] = list(_iter_errors(cards, root))
    errors = [item for item in findings if item["severity"] == "error"]
    warnings = [item for item in findings if item["severity"] == "warning"]
    rarity_counts = Counter(str(card.get("rarity") or "UNKNOWN").upper() for card in cards)
    type_counts = Counter(str(card.get("type") or card.get("card_type") or "UNKNOWN").upper() for card in cards)
    art_ready = sum(1 for card in cards if _asset_exists(root, str(card.get("art") or "")))
    starter_deck_ok = True
    starter_deck_error = None
    try:
        validate_deck_distribution(PLAYER_DECK)
    except Exception as exc:  # noqa: BLE001 - validation report must not crash release page.
        starter_deck_ok = False
        starter_deck_error = str(exc)
        errors.append({"severity": "error", "card_id": "DEFAULT_LOADOUT", "code": "starter_deck_invalid", "message": str(exc)})
    return {
        "version": CONTENT_PIPELINE_VERSION,
        "ok": not errors,
        "card_count": len(cards),
        "starter_deck_ok": starter_deck_ok,
        "starter_deck_error": starter_deck_error,
        "rarity_counts": dict(sorted(rarity_counts.items())),
        "type_counts": dict(sorted(type_counts.items())),
        "art": {
            "ready": art_ready,
            "missing": max(0, len(cards) - art_ready),
            "coverage": round(art_ready / max(1, len(cards)), 3),
        },
        "findings": findings[:80],
        "error_count": len(errors),
        "warning_count": len(warnings),
    }
