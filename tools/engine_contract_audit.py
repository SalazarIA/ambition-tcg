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
    "static/js/game.js",
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
            "start_training",
            "request_match_state",
            "set_intent",
            "play_card",
            "declare_ready",
        ],
        "target_server_to_client": [
            "match_state",
            "battle_event",
            "action_error",
            "match_result",
            "reward_result",
        ],
        "target_payload_schema": {
            "schema": "ambitionz_match_v1",
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
    report.append("1. Create `services/match_state_v1.py` as the only payload builder.")
    report.append("2. Add `request_match_state` socket event.")
    report.append("3. Emit `match_state` while keeping legacy `game_state_update` temporarily.")
    report.append("4. Create `static/js/arena_app.js` to render only from `match_state`.")
    report.append("5. Replace DOM-dependent card actions with `play_card(card_id)`.")
    report.append("6. Remove V5/V7/V8 overlay fallback files from Arena only after stable QA.")
    report.append("7. Reintroduce animations only after card movement is real.")
    report.append("")

    Path("reports").mkdir(exist_ok=True)
    out = Path("reports/engine_contract_audit.md")
    out.write_text("\n".join(report))

    print("\n".join(report))
    print("")
    print(f"REPORT_WRITTEN={out}")

if __name__ == "__main__":
    main()
