#!/usr/bin/env python3
"""Validate Ambitionz card art manifest placeholders and final art paths."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "static" / "assets" / "cards" / "card_art_manifest.json"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
REQUIRED_FIELDS = {
    "id",
    "name",
    "element",
    "type",
    "rarity",
    "art_path",
    "prompt",
    "palette",
    "visual_identity",
    "fallback_gradient",
}
STARTER_IDENTITY_FIELDS = {"role", "simple_use_text", "short_lore"}


def load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"missing manifest: {MANIFEST_PATH}")
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def path_exists(art_path: str) -> bool:
    if not art_path:
        return False
    normalized = art_path.lstrip("/")
    if normalized.startswith("static/"):
        return (ROOT / normalized).exists()
    return (ROOT / "static" / normalized).exists()


def main() -> int:
    manifest = load_manifest()
    cards = manifest.get("cards") or []
    errors: list[str] = []
    warnings: list[str] = []
    ids: list[str] = []
    starter_ids: set[str] = set()
    by_element: Counter[str] = Counter()
    by_type: Counter[str] = Counter()
    by_rarity: Counter[str] = Counter()
    by_role: Counter[str] = Counter()

    try:
        from services.battle_engine_v2 import build_beta_deck

        starter_ids = {str(card.get("id")) for card in build_beta_deck(seed=4248) if card.get("id")}
    except Exception as exc:  # pragma: no cover - defensive QA fallback
        warnings.append(f"starter deck identity check skipped: {exc}")

    if not isinstance(cards, list) or not cards:
        errors.append("manifest has no cards list")

    for index, card in enumerate(cards):
        if not isinstance(card, dict):
            errors.append(f"card #{index} is not an object")
            continue

        missing = sorted(REQUIRED_FIELDS - set(card))
        if missing:
            errors.append(f"{card.get('id', 'unknown')} missing fields: {', '.join(missing)}")

        card_id = str(card.get("id") or "")
        if card_id:
            ids.append(card_id)

        by_element[str(card.get("element") or "Unknown")] += 1
        by_type[str(card.get("type") or "Unknown")] += 1
        by_rarity[str(card.get("rarity") or "Unknown")] += 1
        if card.get("role"):
            by_role[str(card.get("role"))] += 1

        if card_id in starter_ids:
            missing_starter = sorted(STARTER_IDENTITY_FIELDS - set(card))
            empty_starter = sorted(field for field in STARTER_IDENTITY_FIELDS if not str(card.get(field) or "").strip())
            if missing_starter or empty_starter:
                missing_text = ", ".join(sorted(set(missing_starter + empty_starter)))
                errors.append(f"{card_id} starter identity missing: {missing_text}")

        art_path = str(card.get("art_path") or "")
        placeholder = bool(card.get("placeholder", not art_path))
        if art_path and not path_exists(art_path):
            errors.append(f"{card_id} art_path does not exist: {art_path}")
        if placeholder or not art_path:
            warnings.append(f"{card_id or index} uses placeholder art")

    duplicate_ids = [card_id for card_id, count in Counter(ids).items() if count > 1]
    if duplicate_ids:
        errors.append("duplicate ids: " + ", ".join(sorted(duplicate_ids)))

    print("CARD ART MANIFEST CHECK")
    print(f"manifest: {MANIFEST_PATH}")
    print(f"cards: {len(cards)}")
    print("elements:", dict(sorted(by_element.items())))
    print("types:", dict(sorted(by_type.items())))
    print("rarities:", dict(sorted(by_rarity.items())))
    print("roles:", dict(sorted(by_role.items())))
    print(f"starter_identity_cards: {sum(1 for card_id in ids if card_id in starter_ids)}/{len(starter_ids)}")
    print(f"placeholder_warnings: {len(warnings)}")

    for warning in warnings[:8]:
        print("WARN:", warning)
    if len(warnings) > 8:
        print(f"WARN: {len(warnings) - 8} additional placeholder cards")

    if errors:
        for error in errors:
            print("FAIL:", error, file=sys.stderr)
        return 1

    print("PASS: card art manifest is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
