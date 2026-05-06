from pathlib import Path

files = {
    "shop": Path("templates/shop.html").read_text(errors="ignore"),
    "collection": Path("templates/collection.html").read_text(errors="ignore"),
    "deck": Path("templates/deck_builder.html").read_text(errors="ignore"),
    "profile": Path("templates/profile.html").read_text(errors="ignore"),
    "progression": Path("templates/progression.html").read_text(errors="ignore"),
    "css": Path("static/css/card_system_v1.css").read_text(errors="ignore"),
    "booster_js": Path("static/js/booster_opening.js").read_text(errors="ignore"),
}

checks = {
    "css_booster_nav_patch": "Booster Opening Animation + Card Economy Navigation" in files["css"],
    "booster_js_exists": Path("static/js/booster_opening.js").exists(),
    "shop_loads_booster_js": "booster_opening.js" in files["shop"],
    "shop_has_stage": "az-booster-opening-stage-v1" in files["shop"],
    "shop_form_bound": "data-booster-open-form" in files["shop"],
    "shop_result_actions": "az-booster-result-actions-v1" in files["shop"],
    "nav_shop": "az-card-nav-v1" in files["shop"],
    "nav_collection": "az-card-nav-v1" in files["collection"],
    "nav_deck": "az-card-nav-v1" in files["deck"],
    "nav_profile": "az-card-nav-v1" in files["profile"],
    "nav_progression": "az-card-nav-v1" in files["progression"],
    "booster_js_submit_delay": "setTimeout" in files["booster_js"] and "form.submit()" in files["booster_js"],
}

print("# Booster Animation + Nav Polish Audit")

failed = False

for key, ok in checks.items():
    print(("OK" if ok else "FAIL"), key)
    if not ok:
        failed = True

if failed:
    raise SystemExit("BOOSTER_NAV_POLISH_AUDIT_FAILED")

print("BOOSTER_NAV_POLISH_AUDIT_PASSED")
