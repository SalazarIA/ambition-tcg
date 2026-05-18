#!/usr/bin/env python3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


REQUIRED_FILES = [
    "docs/AMBITIONZ_PRODUCT_REBIRTH.md",
    "docs/ASCENSION_DUEL_ARCHITECTURE.md",
    "docs/ASCENSION_DUEL_RULEBOOK.md",
    "docs/AMBITION_CORE_SYSTEM.md",
    "docs/AMBITIONZ_VISUAL_REBIRTH.md",
    "docs/LEGACY_RETIREMENT_PLAN.md",
    "docs/RC_V7_PRODUCT_REBIRTH_STATUS.md",
    "docs/ASCENSION_MIGRATION_REPORT.md",
    "services/ascension_cards.py",
    "services/ascension_engine.py",
    "services/ascension_bot.py",
    "services/ascension_payloads.py",
    "services/ascension_progression.py",
    "templates/arena_ascension.html",
    "static/css/ambitionz_ascension.css",
    "static/js/ambitionz_ascension.js",
    "templates/collection_ascension.html",
    "templates/deck_builder_ascension.html",
    "templates/ascension_history.html",
    "services/ascension_taxonomy.py",
    "services/ascension_history.py",
    "docs/ASCENSION_TAXONOMY_MIGRATION.md",
    "docs/ASCENSION_REWARDS.md",
    "docs/ASCENSION_MATCH_HISTORY.md",
    "docs/ASCENSION_ART_PIPELINE.md",
    "docs/ASCENSION_PUBLIC_COPY.md",
    "docs/LEGACY_CONTAINMENT_CHECKLIST.md",
    "docs/RC_V8_ASCENSION_STATUS.md",
    "docs/ASCENSION_FRONTEND_ARCHITECTURE.md",
    "docs/ASCENSION_VIEWPORT_CONTRACT.md",
    "docs/RC_V8_1_VISUAL_ARCHITECTURE_STATUS.md",
    "tools/qa/qa_ascension_viewport_contract.py",
    "tools/qa/qa_ascension_product_surface.py",
]


def main():
    missing = [path for path in REQUIRED_FILES if not (PROJECT_ROOT / path).exists()]
    assert not missing, f"Missing rebirth files: {missing}"

    app_py = (PROJECT_ROOT / "app.py").read_text()
    template = (PROJECT_ROOT / "templates" / "arena_ascension.html").read_text()
    docs = (PROJECT_ROOT / "docs" / "LEGACY_RETIREMENT_PLAN.md").read_text()

    assert '@app.route("/training")' in app_py
    assert '@app.route("/training-legacy")' in app_py
    assert '@app.route("/api/ascension/start"' in app_py
    assert '@app.route("/collection-ascension")' in app_py
    assert '@app.route("/deck-builder-ascension")' in app_py
    assert '@app.route("/ascension-history")' in app_py
    assert "ax-duel-altar" in template
    assert "/training-legacy" in docs
    print("PASS product_rebirth_report")


if __name__ == "__main__":
    main()
