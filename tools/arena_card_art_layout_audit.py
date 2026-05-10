from pathlib import Path

js = Path("static/js/arena_clean_v48.js").read_text(errors="ignore")
css = Path("static/css/arena_clean_v48.css").read_text(errors="ignore")
adapter = Path("static/js/arena_renderer_adapter.js").read_text(errors="ignore")
be2_adapter = Path("services/battle_engine_v2_adapter.py").read_text(errors="ignore")

checks = {
    "backend_payload_contract": "build_be2_arena_payload" in be2_adapter,
    "backend_is_monster": '"is_monster":' in be2_adapter,
    "js_card_art_image": "az48-art-image" in js,
    "js_rarity_line": "az48-rarity" in js,
    "js_uses_adapter_art": "artUrl" in adapter,
    "css_art_upgrade": ".az48-art-image" in css,
    "css_no_scroll_active": "overflow: hidden !important" in css,
    "css_compact_height": "clamp(208px, 23dvh, 244px)" in css,
    "css_rarity_unique": "rarity-unique" in css,
    "css_art_energy": "@keyframes az48CardEnergy" in css,
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
