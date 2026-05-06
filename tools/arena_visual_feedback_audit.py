from pathlib import Path

js = Path("static/js/arena_app.js").read_text(errors="ignore")
css = Path("static/css/arena_app.css").read_text(errors="ignore")

checks = {
    "js_visualHaptic": "function visualHaptic(kind)" in js,
    "js_flyCardToField": "function flyCardToField" in js,
    "js_markPendingCard": "function markPendingCard" in js,
    "js_buttonImpact": "function buttonImpact" in js,
    "css_flying_card": ".az-flying-card" in css,
    "css_card_fly_keyframes": "@keyframes azCardFlyToField" in css,
    "css_haptic": ".az-haptic-heavy" in css,
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
