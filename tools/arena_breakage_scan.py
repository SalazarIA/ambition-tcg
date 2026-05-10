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
    "static/js/arena_renderer_adapter.js",
    "static/js/arena_clean_v48.js",
    "static/dist/arena3d/arena3d.js",
    "static/js/arena_sound.js",
    "static/css/arena_clean_v48.css",
    "static/css/arena3d.css",
    "services/battle_engine_v2.py",
    "services/battle_engine_v2_adapter.py",
    "services/match_engine_facade.py",
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
    adapter_js = read("static/js/arena_renderer_adapter.js")
    arena_js = read("static/js/arena_clean_v48.js")
    arena3d_js = read("static/dist/arena3d/arena3d.js")
    socket_py = read("sockets/game_socket.py")
    be2 = read("services/battle_engine_v2.py")
    be2_adapter = read("services/battle_engine_v2_adapter.py")
    facade = read("services/match_engine_facade.py")

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
    for path in ["static/js/arena_clean_v48.js"]:
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
    for path in ["static/js/arena_clean_v48.js"]:
        text = read(path)
        for m in re.finditer(r'\.on\(["\']([^"\']+)["\']', text):
            frontend_on.append((path, m.group(1)))
    parts.append(code("\n".join(f"{p}: {e}" for p, e in sorted(set(frontend_on))) or "None found"))

    parts.append(section("Arena HTML Body / Script / CSS"))
    body_lines = line_matches("templates/arena.html", ["<body", "arena_clean_v48.css", "arena3d.css", "arena_renderer_adapter.js", "arena_clean_v48.js", "arena3d.js", "socket.io", "id=", "data-"])
    parts.append(code("\n".join(body_lines[:240]) or "None"))

    parts.append(section("Arena DOM Renderer Definitions"))
    renderer_lines = line_matches("static/js/arena_clean_v48.js", [
        "function render",
        "AmbitionzArena48",
        "az48_state",
        "az48_play_card",
        "az48_declare_ready",
        "az48_set_intent",
        "az48_start_training",
        "querySelector",
        "getElementById",
    ])
    parts.append(code("\n".join(renderer_lines[:260]) or "None"))

    parts.append(section("Renderer Adapter Definitions"))
    adapter_lines = line_matches("static/js/arena_renderer_adapter.js", [
        "function normalizeArenaState",
        "function normalizeCard",
        "function boardSlots",
        "AmbitionzArenaRendererAdapter",
    ])
    parts.append(code("\n".join(adapter_lines[:260]) or "None"))

    parts.append(section("Arena 3D Renderer Definitions"))
    arena3d_lines = line_matches("static/dist/arena3d/arena3d.js", [
        "Arena3D",
        "ambitionz:arena_state_rendered",
        "manifest.json",
        "boardSlots",
    ])
    parts.append(code("\n".join(arena3d_lines[:260]) or "None"))

    parts.append(section("BE2 Match Engine"))
    engine_lines = []
    engine_lines.extend(line_matches("services/battle_engine_v2.py", [
        "def create_match",
        "def play_card",
        "def choose_intent",
        "def resolve_round",
        "def start_round",
        "def _remove_card_from_hand",
    ]))
    engine_lines.extend(line_matches("services/match_engine_facade.py", [
        "class MatchEngineFacade",
        "def start_training",
        "def start_bot_match",
        "def start_pvp_match",
        "def emit_state",
        "def play_card",
        "def ready",
    ]))
    parts.append(code("\n".join(engine_lines[:260]) or "None"))

    parts.append(section("BE2 Payload Contract"))
    payload_lines = line_matches("services/battle_engine_v2_adapter.py", [
        "def build_be2_arena_payload",
        "def _player_payload",
        "def _battle_card_to_arena_card",
        '"me"',
        '"enemy"',
        '"hand"',
        '"legal_actions"',
        '"playable_card_ids"',
    ])
    parts.append(code("\n".join(payload_lines[:220]) or "None"))

    parts.append(section("CSS Arena Locks"))
    css_lines = line_matches("static/css/arena_clean_v48.css", [
        "az48-renderer-3d",
        "az48-card-v2",
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

    if ("arena" + "_app.js") in arena_html or ("game" + ".js") in arena_html:
        issues.append("Template still loads a legacy arena renderer.")

    if "az48_play_card" in arena_js and "az48_play_card" not in app and "az48_play_card" not in socket_py:
        issues.append("Frontend emits az48_play_card but backend listener may not exist.")

    if "az48_declare_ready" in arena_js and "az48_declare_ready" not in app and "az48_declare_ready" not in socket_py:
        issues.append("Frontend emits az48_declare_ready but backend listener may not exist.")

    if "az48_set_intent" in arena_js and "az48_set_intent" not in app and "az48_set_intent" not in socket_py:
        issues.append("Frontend emits az48_set_intent but backend listener may not exist.")

    if "az48_start_training" in arena_js and "az48_start_training" not in app and "az48_start_training" not in socket_py:
        issues.append("Frontend emits az48_start_training but backend listener may not exist.")

    if "function normalizeArenaState" not in adapter_js:
        issues.append("Renderer adapter is missing normalizeArenaState.")

    if arena_html.count("arena_clean_v48.js") != 1:
        issues.append("Template should load the clean DOM arena exactly once.")

    if "build_be2_arena_payload" not in be2_adapter:
        issues.append("BE2 adapter is missing build_be2_arena_payload.")

    if "class MatchEngineFacade" not in facade:
        issues.append("Arena is missing the BE2 match-engine facade.")

    if "def play_card" not in be2:
        issues.append("BE2 engine is missing play_card.")

    parts.append(code("\n".join(f"- {i}" for i in issues) or "No obvious fatal issue detected by static scan."))

    REPORT.write_text("\n".join(parts))
    print(REPORT)

if __name__ == "__main__":
    main()
