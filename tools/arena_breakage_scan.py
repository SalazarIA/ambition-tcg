from pathlib import Path
import re
import json
import sys
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

REPORT = PROJECT_ROOT / "reports" / f"arena_breakage_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

FILES = [
    "app.py",
    "templates/arena.html",
    "static/js/game.js",
    "static/js/arena_app.js",
    "static/js/arena_sound.js",
    "static/css/arena_app.css",
    "services/match_state_v1.py",
    "services/match_actions_v1.py",
    "services/arena_payload.py",
    "sockets/game_socket.py",
]

def read(path):
    p = PROJECT_ROOT / path
    if not p.exists():
        return ""
    return p.read_text(errors="ignore")

def section(title):
    return f"\n\n## {title}\n\n"

def code(text):
    return "```text\n" + str(text).strip() + "\n```\n"

def find_all(pattern, text):
    return sorted(set(re.findall(pattern, text)))

def line_matches(path, patterns):
    text = read(path)
    out = []
    for i, line in enumerate(text.splitlines(), start=1):
        if any(p in line for p in patterns):
            out.append(f"{path}:{i}: {line}")
    return out

def main():
    parts = []
    parts.append(f"# Ambitionz Arena Breakage Scan\n\nGenerated: {datetime.now().isoformat()}\n")

    parts.append(section("Files Present"))
    for f in FILES:
        p = PROJECT_ROOT / f
        parts.append(f"- {f}: {'OK' if p.exists() else 'MISSING'}")

    app = read("app.py")
    arena_html = read("templates/arena.html")
    game_js = read("static/js/game.js")
    arena_js = read("static/js/arena_app.js")
    socket_py = read("sockets/game_socket.py")
    match_actions = read("services/match_actions_v1.py")
    match_state = read("services/match_state_v1.py")

    parts.append(section("Socket Events - Backend Listeners"))
    backend_events = []
    for path in ["app.py", "sockets/game_socket.py"]:
        text = read(path)
        for m in re.finditer(r'@socketio\.on\(["\']([^"\']+)["\']\)', text):
            backend_events.append((path, m.group(1)))
        for m in re.finditer(r'\.on\(["\']([^"\']+)["\']', text):
            if "socketio" in text[max(0, m.start()-80):m.start()+20]:
                backend_events.append((path, m.group(1)))
    parts.append(code("\n".join(f"{p}: {e}" for p, e in sorted(set(backend_events))) or "None found"))

    parts.append(section("Socket Events - Frontend Emits"))
    frontend_emits = []
    for path in ["static/js/game.js", "static/js/arena_app.js"]:
        text = read(path)
        for m in re.finditer(r'\.emit\(["\']([^"\']+)["\']', text):
            frontend_emits.append((path, m.group(1)))
        for m in re.finditer(r'emit\(["\']([^"\']+)["\']', text):
            frontend_emits.append((path, m.group(1)))
    parts.append(code("\n".join(f"{p}: {e}" for p, e in sorted(set(frontend_emits))) or "None found"))

    backend_event_names = {e for _, e in backend_events}
    frontend_emit_names = {e for _, e in frontend_emits}
    parts.append(section("Frontend Emits Without Backend Listener"))
    missing_backend = sorted(frontend_emit_names - backend_event_names)
    parts.append(code("\n".join(missing_backend) or "OK"))

    parts.append(section("Backend Listeners Not Emitted By Frontend"))
    missing_frontend = sorted(backend_event_names - frontend_emit_names)
    parts.append(code("\n".join(missing_frontend) or "OK"))

    parts.append(section("Frontend Socket On Handlers"))
    frontend_on = []
    for path in ["static/js/game.js", "static/js/arena_app.js"]:
        text = read(path)
        for m in re.finditer(r'\.on\(["\']([^"\']+)["\']', text):
            frontend_on.append((path, m.group(1)))
    parts.append(code("\n".join(f"{p}: {e}" for p, e in sorted(set(frontend_on))) or "None found"))

    parts.append(section("Arena HTML Body / Script / CSS"))
    body_lines = line_matches("templates/arena.html", ["<body", "arena_app.css", "arena_app.js", "game.js", "socket.io", "id=", "data-"])
    parts.append(code("\n".join(body_lines[:240]) or "None"))

    parts.append(section("Arena Renderer Definitions"))
    renderer_lines = line_matches("static/js/arena_app.js", [
        "function render",
        "renderArenaV45",
        "AmbitionzArenaV45",
        "AmbitionzArenaV46",
        "game_state_update",
        "match_state",
        "play_card",
        "declare_ready",
        "set_intent",
        "start_training",
        "querySelector",
        "getElementById",
    ])
    parts.append(code("\n".join(renderer_lines[:260]) or "None"))

    parts.append(section("Legacy game.js Renderer Definitions"))
    game_lines = line_matches("static/js/game.js", [
        "function render",
        "socket.on",
        "socket.emit",
        "play_card",
        "declare_ready",
        "set_intent",
        "start_training",
        "getElementById",
        "byId",
        "hand",
    ])
    parts.append(code("\n".join(game_lines[:260]) or "None"))

    parts.append(section("Backend V1 Match Actions"))
    action_lines = line_matches("services/match_actions_v1.py", [
        "def create_training_match_v1",
        "def play_card",
        "def declare_ready",
        "def set_intent",
        "def",
        "hand",
        "field",
        "events",
    ])
    parts.append(code("\n".join(action_lines[:260]) or "None"))

    parts.append(section("Payload Contract"))
    payload_lines = line_matches("services/match_state_v1.py", [
        "def build_match_state_v1",
        "def build_match_state_payloads",
        "def normalize_player",
        '"me"',
        '"enemy"',
        '"hand"',
        '"legal_actions"',
        '"playable_card_ids"',
    ])
    parts.append(code("\n".join(payload_lines[:220]) or "None"))

    parts.append(section("CSS Arena Locks"))
    css_lines = line_matches("static/css/arena_app.css", [
        "az-arena-v45",
        "az-arena-v40",
        "display: none",
        "overflow",
        "position: fixed",
        "z-index",
        "height: 100dvh",
        "body",
        "main",
    ])
    parts.append(code("\n".join(css_lines[-260:]) or "None"))

    parts.append(section("Potential Fatal Issues Detected"))
    issues = []

    if 'body.az-arena-v45 > main:not(#az-arena-v45-root)' in read("static/css/arena_app.css"):
        issues.append("CSS hides all existing main elements except #az-arena-v45-root. If V45 root does not receive socket state, the arena appears dead.")

    if "play_card_v1" in arena_js and "play_card_v1" not in app and "play_card_v1" not in socket_py:
        issues.append("Frontend emits play_card_v1 but backend listener may not exist.")

    if "declare_ready_v1" in arena_js and "declare_ready_v1" not in app and "declare_ready_v1" not in socket_py:
        issues.append("Frontend emits declare_ready_v1 but backend listener may not exist.")

    if "set_intent_v1" in arena_js and "set_intent_v1" not in app and "set_intent_v1" not in socket_py:
        issues.append("Frontend emits set_intent_v1 but backend listener may not exist.")

    if "start_training_v1" in arena_js and "start_training_v1" not in app and "start_training_v1" not in socket_py:
        issues.append("Frontend emits start_training_v1 but backend listener may not exist.")

    if "AmbitionzArenaV45" in arena_js and "game_state_update" in game_js:
        issues.append("Multiple renderers likely active: game.js legacy renderer + arena_app.js V45 renderer. They may compete or listen to different payload contracts.")

    if "build_match_state_v1" in match_state and "me.hand" not in arena_js and "match.me.hand" in arena_js:
        issues.append("Renderer may expect match.me.hand indirectly; verify normalize path.")

    parts.append(code("\n".join(f"- {i}" for i in issues) or "No obvious fatal issue detected by static scan."))

    REPORT.write_text("\n".join(parts))
    print(REPORT)

if __name__ == "__main__":
    main()
