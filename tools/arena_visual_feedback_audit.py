from pathlib import Path

js = Path("static/js/arena_clean_v48.js").read_text(errors="ignore")
css = Path("static/css/arena_clean_v48.css").read_text(errors="ignore")
adapter = Path("static/js/arena_renderer_adapter.js").read_text(errors="ignore")

checks = {
    "js_dispatches_render_event": "ambitionz:arena_state_rendered" in js,
    "js_uses_renderer_adapter": "AmbitionzArenaRendererAdapter" in js,
    "adapter_normalizes_cards": "function normalizeCard" in adapter,
    "adapter_board_slots": "function boardSlots" in adapter,
    "css_card_depth": ".az48-card-v2" in css,
    "css_card_sheen": ".az48-card-sheen" in css,
    "css_card_energy_keyframes": "@keyframes az48CardEnergy" in css,
    "css_card_art_image": ".az48-art-image" in css,
    "css_no_audio_reference": "audio" not in js.lower(),
}

print("# Arena Visual Feedback Audit")

failed = False

for key, ok in checks.items():
    print(("OK" if ok else "FAIL"), key)
    if not ok:
        failed = True

if failed:
    raise SystemExit("ARENA_VISUAL_FEEDBACK_AUDIT_FAILED")

print("ARENA_VISUAL_FEEDBACK_AUDIT_PASSED")
