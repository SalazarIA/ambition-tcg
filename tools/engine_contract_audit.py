from pathlib import Path
import re
import json
from collections import defaultdict

FILES = [
    "app.py",
    "game/state.py",
    "game/battle.py",
    "game/deck.py",
    "game/engine.py",
    "game/cards.py",
    "game/match_utils.py",
    "game/matchmaking.py",
    "game/bot_ai.py",
    "services/match_payloads.py",
    "services/arena_payload.py",
    "services/battle_summary.py",
    "services/match_telemetry.py",
    "static/js/arena_renderer_adapter.js",
    "static/js/arena_clean_v48.js",
    "templates/arena.html",
]

SOCKET_PATTERNS = {
    "backend_socket_listeners": r'@socketio\.on\(["\\\']([^"\\\']+)["\\\']\)',
    "backend_socket_emits": r'socketio\.emit\(["\\\']([^"\\\']+)["\\\']',
    "frontend_socket_emits": r'socket\.emit\(["\\\']([^"\\\']+)["\\\']',
    "frontend_socket_listeners": r'socket\.on\(["\\\']([^"\\\']+)["\\\']',
}

KEYWORDS = [
    "hand",
    "deck",
    "field",
    "monster",
    "spell",
    "trap",
    "graveyard",
    "intent",
    "ready",
    "energy",
    "ambition",
    "hp",
    "play_card",
    "set_intent",
    "declare_ready",
    "game_state_update",
    "battle_log",
    "post_match_summary",
    "reward",
]

def read(path):
    p = Path(path)
    return p.read_text(errors="ignore") if p.exists() else ""

def find_socket_events():
    result = defaultdict(lambda: defaultdict(int))

    for file in FILES:
        text = read(file)
        if not text:
            continue

        for label, pattern in SOCKET_PATTERNS.items():
            for match in re.findall(pattern, text):
                result[label][match] += 1

    return result

def keyword_counts():
    result = {}

    for file in FILES:
        text = read(file)
        if not text:
            continue

        counts = {}

        for keyword in KEYWORDS:
            counts[keyword] = len(re.findall(re.escape(keyword), text, flags=re.IGNORECASE))

        result[file] = counts

    return result

def find_functions():
    result = {}

    for file in FILES:
        text = read(file)
        if not text:
            continue

        funcs = re.findall(r'^\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', text, flags=re.MULTILINE)
        js_funcs = re.findall(r'^\s*function\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', text, flags=re.MULTILINE)
        result[file] = {
            "python_functions": funcs,
            "js_functions": js_funcs,
        }

    return result

def extract_emit_blocks():
    blocks = []

    for file in FILES:
        text = read(file)
        if not text:
            continue

        lines = text.splitlines()

        for i, line in enumerate(lines, start=1):
            if "game_state_update" in line or "play_card" in line or "set_intent" in line or "ready" in line:
                start = max(1, i - 4)
                end = min(len(lines), i + 8)
                snippet = "\n".join(f"{n:04d}: {lines[n-1]}" for n in range(start, end + 1))
                blocks.append({
                    "file": file,
                    "line": i,
                    "snippet": snippet,
                })

    return blocks

def build_contract_recommendation(socket_events):
    backend_listeners = set(socket_events["backend_socket_listeners"].keys())
    backend_emits = set(socket_events["backend_socket_emits"].keys())
    frontend_emits = set(socket_events["frontend_socket_emits"].keys())
    frontend_listeners = set(socket_events["frontend_socket_listeners"].keys())

    return {
        "current_backend_listeners": sorted(backend_listeners),
        "current_backend_emits": sorted(backend_emits),
        "current_frontend_emits": sorted(frontend_emits),
        "current_frontend_listeners": sorted(frontend_listeners),
        "missing_backend_listener_for_frontend_emit": sorted(frontend_emits - backend_listeners),
        "missing_frontend_listener_for_backend_emit": sorted((backend_emits - frontend_listeners) - {"connect", "disconnect"}),
        "target_client_to_server": [
            "az48_start_training",
            "az48_request_state",
            "az48_set_intent",
            "az48_play_card",
            "az48_declare_ready",
        ],
        "target_server_to_client": [
            "az48_state",
            "game_state_update",
            "action_error",
            "game_over",
            "post_match_summary",
        ],
        "target_payload_schema": {
            "schema": "ambitionz_arena_clean_v50",
            "match_id": "string",
            "mode": "training|pvp|bot",
            "round": "number",
            "phase": "draw|intent|main|ready|resolve|finished",
            "me": {
                "hp": "number",
                "energy": "number",
                "max_energy": "number",
                "ambition": "number",
                "intent": "Strike|Guard|Focus|null",
                "ready": "boolean",
                "hand": "card[]",
                "field": {
                    "monster": "card|null",
                    "spell": "card|null",
                    "trap": "card|null"
                },
                "deck_count": "number",
                "graveyard_count": "number"
            },
            "enemy": {
                "hp": "number",
                "energy": "number",
                "max_energy": "number",
                "ambition": "number",
                "intent": "hidden|revealed",
                "ready": "boolean",
                "hand_count": "number",
                "field": {
                    "monster": "card|null",
                    "spell": "card|null",
                    "trap": "card|null"
                }
            },
            "legal_actions": {
                "can_choose_intent": "boolean",
                "can_play_cards": "boolean",
                "can_ready": "boolean",
                "playable_card_ids": "string[]"
            },
            "message": "string"
        }
    }

def main():
    socket_events = find_socket_events()
    counts = keyword_counts()
    functions = find_functions()
    blocks = extract_emit_blocks()
    contract = build_contract_recommendation(socket_events)

    report = []
    report.append("# Ambitionz — Engine Contract Audit")
    report.append("")
    report.append("## Purpose")
    report.append("")
    report.append("This audit maps the current battle engine, socket events, payloads and frontend dependencies before the fullstack Arena rebuild.")
    report.append("")
    report.append("## Socket Events")
    report.append("")

    for group, events in socket_events.items():
        report.append(f"### {group}")
        if events:
            for event, count in sorted(events.items()):
                report.append(f"- {event}: {count}")
        else:
            report.append("- None")
        report.append("")

    report.append("## Socket Contract Gaps")
    report.append("")
    for item in contract["missing_backend_listener_for_frontend_emit"]:
        report.append(f"- Frontend emits but backend listener missing: `{item}`")

    for item in contract["missing_frontend_listener_for_backend_emit"]:
        report.append(f"- Backend emits but frontend listener missing: `{item}`")

    if not contract["missing_backend_listener_for_frontend_emit"] and not contract["missing_frontend_listener_for_backend_emit"]:
        report.append("- No obvious socket event gaps found.")
    report.append("")

    report.append("## Keyword Counts")
    report.append("")
    for file, file_counts in counts.items():
        report.append(f"### {file}")
        active = {k: v for k, v in file_counts.items() if v}
        if active:
            for key, value in sorted(active.items()):
                report.append(f"- {key}: {value}")
        else:
            report.append("- No relevant keywords found.")
        report.append("")

    report.append("## Functions Found")
    report.append("")
    for file, groups in functions.items():
        report.append(f"### {file}")
        if groups["python_functions"]:
            report.append("Python:")
            for fn in groups["python_functions"]:
                report.append(f"- {fn}")
        if groups["js_functions"]:
            report.append("JavaScript:")
            for fn in groups["js_functions"]:
                report.append(f"- {fn}")
        if not groups["python_functions"] and not groups["js_functions"]:
            report.append("- None")
        report.append("")

    report.append("## Important Snippets")
    report.append("")
    for block in blocks[:80]:
        report.append(f"### {block['file']}:{block['line']}")
        report.append("```text")
        report.append(block["snippet"])
        report.append("```")
        report.append("")

    report.append("## Target Fullstack Contract")
    report.append("")
    report.append("```json")
    report.append(json.dumps(contract["target_payload_schema"], indent=2, ensure_ascii=False))
    report.append("```")
    report.append("")

    report.append("## Recommended Rebuild Order")
    report.append("")
    report.append("1. Keep BE2 as the canonical match engine for training, bot and PvP.")
    report.append("2. Keep `static/js/arena_renderer_adapter.js` as the client render contract.")
    report.append("3. Emit canonical `az48_state` for DOM and WebGL renderers.")
    report.append("4. Keep `static/js/arena_clean_v48.js` as the only active DOM arena client.")
    report.append("5. Add Three.js renderer features behind `?renderer=3d` without duplicating rules.")
    report.append("6. Remove any new legacy fallback only after stable browser QA.")
    report.append("")

    Path("reports").mkdir(exist_ok=True)
    out = Path("reports/engine_contract_audit.md")
    out.write_text("\n".join(report))

    print("\n".join(report))
    print("")
    print(f"REPORT_WRITTEN={out}")

if __name__ == "__main__":
    main()
