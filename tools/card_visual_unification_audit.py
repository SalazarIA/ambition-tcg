from pathlib import Path

checks = {
    "card_system_css": Path("static/css/card_system_v1.css").exists(),
    "collection_loads_css": "card_system_v1.css" in Path("templates/collection.html").read_text(errors="ignore"),
    "deck_builder_loads_css": "card_system_v1.css" in Path("templates/deck_builder.html").read_text(errors="ignore"),
    "shop_loads_css": "card_system_v1.css" in Path("templates/shop.html").read_text(errors="ignore"),
    "collection_az_card": "az-card-v1" in Path("templates/collection.html").read_text(errors="ignore"),
    "starter_service": Path("services/starter_deck_v1.py").exists(),
    "actions_uses_starter": "build_balanced_starter_deck" in Path("services/match_actions_v1.py").read_text(errors="ignore"),
}

print("# Card Visual Unification Audit")

failed = False

for key, ok in checks.items():
    print(("OK" if ok else "FAIL"), key)
    if not ok:
        failed = True

if failed:
    raise SystemExit("CARD_VISUAL_UNIFICATION_AUDIT_FAILED")

print("CARD_VISUAL_UNIFICATION_AUDIT_PASSED")
