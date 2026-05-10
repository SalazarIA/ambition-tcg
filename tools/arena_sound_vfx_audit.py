from pathlib import Path

files = {
    "arena_sound_js": Path("static/js/arena_sound.js").read_text(errors="ignore"),
    "arena_js": Path("static/js/arena_clean_v48.js").read_text(errors="ignore"),
    "arena_css": Path("static/css/arena_clean_v48.css").read_text(errors="ignore"),
    "arena_html": Path("templates/arena.html").read_text(errors="ignore"),
}

checks = {
    "sound_file_exists": Path("static/js/arena_sound.js").exists(),
    "web_audio_context": "AudioContext" in files["arena_sound_js"],
    "mute_button": "az-sound-toggle" in files["arena_sound_js"] and "az-sound-toggle" in files["arena_css"],
    "clean_arena_uses_sound": "function playSound(name, payload)" in files["arena_js"],
    "card_fly_sound": 'playSound("cardFly"' in files["arena_js"],
    "card_impact_sound": 'playSound("cardImpact"' in files["arena_js"],
    "intent_sound": 'playSound("intent"' in files["arena_js"],
    "ready_sound": 'playSound("ready"' in files["arena_js"],
    "damage_sound": 'playSound("damage"' in files["arena_js"],
    "card_vfx_depth": "az48-card-v2" in files["arena_css"] and "az48-card-sheen" in files["arena_css"],
    "html_loads_sound": "arena_sound.js" in files["arena_html"],
}

print("# Arena Sound + VFX Audit")

failed = False

for key, ok in checks.items():
    print(("OK" if ok else "FAIL"), key)
    if not ok:
        failed = True

if failed:
    raise SystemExit("ARENA_SOUND_VFX_AUDIT_FAILED")

print("ARENA_SOUND_VFX_AUDIT_PASSED")
