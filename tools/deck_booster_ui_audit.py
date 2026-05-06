from pathlib import Path

files = {
    "deck_builder": Path("templates/deck_builder.html").read_text(errors="ignore"),
    "shop": Path("templates/shop.html").read_text(errors="ignore"),
    "css": Path("static/css/card_system_v1.css").read_text(errors="ignore"),
}

checks = {
    "css_extensions": "Deck Builder + Booster Card UI Extensions" in files["css"],
    "deck_loads_css": "card_system_v1.css" in files["deck_builder"],
    "deck_unified_class": "deck-builder-unified-v1" in files["deck_builder"],
    "deck_safe_style": "deck-builder-unified-v1 .card-grid" in files["deck_builder"],
    "shop_loads_css": "card_system_v1.css" in files["shop"],
    "shop_booster_result": "is-booster-result-card" in files["shop"],
    "shop_booster_stamp": "az-booster-rarity-stamp-v1" in files["shop"],
    "css_booster_reveal": "azBoosterCardReveal" in files["css"],
    "css_deck_controls": "az-card-deck-controls-v1" in files["css"],
}

print("# Deck Builder + Booster UI Audit")

failed = False

for key, ok in checks.items():
    print(("OK" if ok else "FAIL"), key)
    if not ok:
        failed = True

if failed:
    raise SystemExit("DECK_BOOSTER_UI_AUDIT_FAILED")

print("DECK_BOOSTER_UI_AUDIT_PASSED")
