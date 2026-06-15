#!/usr/bin/env python3
"""Report bespoke card-art coverage (audit débito: ~20/103).

Distinguishes BESPOKE art (committed *-art.webp referenced by the asset
manifest) from the optimized/fallback path that every other card uses, and
flags high-priority cards (legendaries) still without bespoke art. Producing
the art itself is human/asset work — this surfaces the gap and prioritises it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from services.rebirth_cards import catalog_payload  # noqa: E402
from services.rebirth_content_pipeline import content_pipeline_report  # noqa: E402

MANIFEST = PROJECT_ROOT / "static" / "assets" / "rebirth" / "manifest.json"


BESPOKE_STATUSES = {"rebirth_legendary_contract", "bespoke", "premium"}


def bespoke_coverage() -> dict:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest_paths = set(manifest.get("cards", {}).values())
    cards = catalog_payload()
    total = len(cards)

    def is_bespoke(card) -> bool:
        status = str(card.get("art_status") or "").lower()
        return status in BESPOKE_STATUSES or str(card.get("art") or "") in manifest_paths

    bespoke = [c for c in cards if is_bespoke(c)]
    legendaries_missing = [
        c["id"] for c in cards
        if str(c.get("rarity")).upper() == "LEGENDARY" and not is_bespoke(c)
    ]
    return {
        "catalog": total,
        "bespoke_cards": len(bespoke),
        "bespoke_coverage": round(len(bespoke) / max(1, total), 3),
        "manifest_bespoke_files": len(manifest.get("cards", {})),
        "optimized_webp_fallback": sum(
            1 for c in cards if str(c.get("art_status") or "").lower() == "optimized_webp_path"
        ),
        "legendaries_missing_bespoke": legendaries_missing,
        "pipeline_art_ready": content_pipeline_report().get("art", {}),
        "targets": {"beta": 0.50, "public": 0.80},
        "note": "pipeline_art_ready=1.0 conta arte funcional (inclui fallback); bespoke_cards e o debito real.",
    }


def main() -> int:
    print(json.dumps(bespoke_coverage(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
