from pathlib import Path

js = Path("static/js/arena_app.js").read_text(errors="ignore")
css = Path("static/css/arena_app.css").read_text(errors="ignore")
state = Path("services/match_state_v1.py").read_text(errors="ignore")

checks = {
    "backend_element_css": '"element_css":' in state,
    "backend_is_monster": '"is_monster":' in state,
    "js_card_art_orb": "az-card-art-orb" in js,
    "js_rarity_line": "az-card-rarity-line" in js,
    "js_recalibrate_viewport": "function recalibrateArenaViewport()" in js,
    "css_art_upgrade": "Card Art Placeholder Upgrade + AAA Layout QA" in css,
    "css_no_scroll_active": "overflow: hidden !important" in css,
    "css_compact_height": "az-compact-height" in css,
    "css_rarity_unique": "rarity-unique" in css,
    "css_art_energy": "@keyframes azArtEnergySlow" in css,
}

print("# Arena Card Art Layout Audit")

failed = False

for key, ok in checks.items():
    print(("OK" if ok else "FAIL"), key)
    if not ok:
        failed = True

if failed:
    raise SystemExit("ARENA_CARD_ART_LAYOUT_AUDIT_FAILED")

print("ARENA_CARD_ART_LAYOUT_AUDIT_PASSED")
