
from pathlib import Path
from datetime import datetime
import re
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

REPORT_DIR = PROJECT_ROOT / "reports" / "qa"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
REPORT = REPORT_DIR / f"arena_systems_audit_{STAMP}.md"

FILES = {
    "template": PROJECT_ROOT / "templates" / "arena.html",
    "arena_js": PROJECT_ROOT / "static" / "js" / "arena_clean_v48.js",
    "arena_css": PROJECT_ROOT / "static" / "css" / "arena_clean_v48.css",
    "app": PROJECT_ROOT / "app.py",
    "match_actions": PROJECT_ROOT / "services" / "match_actions_v1.py",
    "arena_state": PROJECT_ROOT / "services" / "arena_clean_state.py",
    "socket_legacy": PROJECT_ROOT / "sockets" / "game_socket.py",
}

def read(path):
    return path.read_text(errors="ignore") if path.exists() else ""

def code_block(text):
    return "```text\n" + str(text).strip() + "\n```"

def find_lines(text, patterns):
    out = []
    for i, line in enumerate(text.splitlines(), start=1):
        for pattern in patterns:
            if pattern in line:
                out.append(f"{i}: {line}")
                break
    return out

def section(lines, title):
    lines.append("")
    lines.append(f"## {title}")
    lines.append("")

def check_contract(lines, template, arena_js, app):
    section(lines, "1. Contract Audit")

    required_dom_ids = [
        "az48-start",
        "az48-strike",
        "az48-guard",
        "az48-focus",
        "az48-ready",
        "az48-hand",
        "az48-me-field",
        "az48-enemy-field",
        "az48-message",
        "az48-round",
        "az48-phase",
    ]

    required_events = [
        "az48_start_training",
        "az48_set_intent",
        "az48_play_card",
        "az48_declare_ready",
        "az48_state",
    ]

    dom = [f"- {dom_id}: {'OK' if dom_id in template else 'MISSING'}" for dom_id in required_dom_ids]
    events = [
        f"- {event}: JS={'OK' if event in arena_js else 'MISSING'} | backend={'OK' if event in app else 'MISSING'}"
        for event in required_events
    ]

    lines.append("### DOM IDs")
    lines.append(code_block("\n".join(dom)))
    lines.append("")
    lines.append("### Socket/Event Contract")
    lines.append(code_block("\n".join(events)))

def check_legacy_conflicts(lines, template, arena_js, app):
    section(lines, "2. Legacy Conflict Audit")

    conflict_terms = [
        "play_to_field",
        "choose_intent",
        "declare_ready",
        "start_training",
        "game_state_update",
        "arena_app.js",
        "game.js",
        "arena_state_bridge.js",
        "az-arena-v45",
        "az-arena-v40",
    ]

    findings = []
    for term in conflict_terms:
        count = template.count(term) + arena_js.count(term) + app.count(term)
        if count:
            findings.append(f"- {term}: {count}")

    if not findings:
        findings.append("No obvious legacy conflict terms found.")

    lines.append(code_block("\n".join(findings)))

    risk = []
    if "play_to_field" in arena_js:
        risk.append("P0: arena JS still emits legacy play_to_field.")
    play_card_match = re.search(r"function playCard\(id\)\s*\{(?P<body>.*?)(?:\n\s*function\s+|\n\s*if \(|\n\s*document\.)", arena_js, re.S)
    play_card_body = play_card_match.group("body") if play_card_match else ""
    if "c.id" in play_card_body:
        risk.append("P0: arena playCard still references undefined-risk c.id.")
    if "emit(\"declare_ready\"" in arena_js:
        risk.append("P1: arena JS still emits legacy declare_ready.")
    if "game_state_update" in arena_js:
        risk.append("P1: clean arena still listens to game_state_update; must schema-filter.")
    if "game.js" in template and "arena_clean_v48.js" in template:
        risk.append("P0/P1: template may load legacy game.js and clean arena JS together.")
    if "arena_app.js" in template and "arena_clean_v48.js" in template:
        risk.append("P0/P1: template may load arena_app.js and clean arena JS together.")

    if not risk:
        risk.append("No fatal legacy-renderer risk detected by static audit.")

    lines.append("")
    lines.append("### Risk Summary")
    lines.append(code_block("\n".join(risk)))

def check_play_card_function(lines, arena_js):
    section(lines, "3. Play Card Function Audit")

    match = re.search(r"function playCard\(id\)\s*\{(?P<body>.*?)(?:\n\s*function\s+|\n\s*if \(|\n\s*document\.)", arena_js, re.S)

    if not match:
        lines.append(code_block("P0: function playCard(id) not found."))
        return

    body = match.group("body")
    lines.append(code_block(body[:3000]))
    lines.append("")

    assertions = [
        f"- Uses az48_play_card: {'OK' if 'az48_play_card' in body else 'MISSING'}",
        f"- Uses legacy play_to_field: {'FAIL' if 'play_to_field' in body else 'OK'}",
        f"- Uses undefined c.id: {'FAIL' if 'c.id' in body else 'OK'}",
        f"- Sends card_id from id: {'OK' if 'card_id: id' in body else 'CHECK'}",
        f"- Shows Playing card feedback: {'OK' if 'Playing card' in body else 'CHECK'}",
    ]

    lines.append("### Assertions")
    lines.append(code_block("\n".join(assertions)))

def check_backend_handlers(lines, app):
    section(lines, "4. Backend Handler Audit")

    patterns = [
        '@socketio.on("az48_start_training")',
        '@socketio.on("az48_request_state")',
        '@socketio.on("az48_set_intent")',
        '@socketio.on("az48_play_card")',
        '@socketio.on("az48_declare_ready")',
        "def emit_az48_state_for_sid",
        "build_arena_clean_state",
    ]

    found = [f"- {pattern}: {'OK' if pattern in app else 'MISSING'}" for pattern in patterns]
    lines.append(code_block("\n".join(found)))
    lines.append("")

    relevant = find_lines(app, [
        "az48_start_training",
        "az48_set_intent",
        "az48_play_card",
        "az48_declare_ready",
        "emit_az48_state_for_sid",
        "build_arena_clean_state",
    ])

    lines.append("### Relevant lines")
    lines.append(code_block("\n".join(relevant[:140])))

def check_state_architecture(lines, arena_state, match_actions):
    section(lines, "5. State Architecture Audit")

    checks = [
        ("arena_clean_state has build_arena_clean_state", "def build_arena_clean_state" in arena_state),
        ("arena_clean_state includes legal_actions", "legal_actions" in arena_state),
        ("arena_clean_state includes playable_card_ids", "playable_card_ids" in arena_state),
        ("match_actions has play_card", "def play_card" in match_actions),
        ("match_actions removes card from hand", ".pop(" in match_actions and "hand" in match_actions),
        ("match_actions has declare_ready", "def declare_ready" in match_actions),
        ("match_actions references round/resolve", "round" in match_actions.lower() or "resolve" in match_actions.lower()),
    ]

    lines.append(code_block("\n".join(f"- {name}: {'OK' if ok else 'CHECK'}" for name, ok in checks)))

def recommendations(lines, template, arena_js, app):
    section(lines, "6. Engineering Recommendations")

    recs = []

    if "play_to_field" in arena_js:
        recs.append("P0: Remove play_to_field from clean arena. Use az48_play_card only.")
    if "c.id" in arena_js:
        recs.append("P0: Fix undefined c.id in playCard. Use id or resolve card object from latestState.")
    if "game_state_update" in arena_js:
        recs.append("P1: Keep schema filter strict for game_state_update or remove listener entirely.")
    if "az48-hand" not in template:
        recs.append("P0: Template must expose #az48-hand.")
    if "az48-ready" not in template:
        recs.append("P0: Template must expose #az48-ready.")
    if "az48_play_card" not in app:
        recs.append("P0: Backend must expose az48_play_card handler.")
    if "az48_state" not in arena_js:
        recs.append("P0: Frontend must listen to az48_state.")

    recs.extend([
        "Architecture target: one arena renderer, one payload schema, one event namespace.",
        "Do not let clean arena depend on legacy game.js or battle_actions socket handlers.",
        "Every browser QA run must verify: hand decreases, field increases, HP/round changes, no stuck message.",
        "Production QA should verify cache bust version and service worker update before visual testing.",
    ])

    lines.append(code_block("\n".join(f"- {r}" for r in recs)))

def main():
    template = read(FILES["template"])
    arena_js = read(FILES["arena_js"])
    app = read(FILES["app"])
    match_actions = read(FILES["match_actions"])
    arena_state = read(FILES["arena_state"])

    lines = [
        "# Ambitionz Arena Systems Audit",
        "",
        f"- Generated: {STAMP}",
        "",
    ]

    check_contract(lines, template, arena_js, app)
    check_legacy_conflicts(lines, template, arena_js, app)
    check_play_card_function(lines, arena_js)
    check_backend_handlers(lines, app)
    check_state_architecture(lines, arena_state, match_actions)
    recommendations(lines, template, arena_js, app)

    REPORT.write_text("\n".join(lines))
    print(REPORT)

def run_systems_audit():
    main()
    body = REPORT.read_text(errors="ignore")
    fatal_markers = [
        "P0:",
        "MISSING",
        "FAIL",
        "function playCard(id) not found",
    ]

    status = "PASS"
    errors = []

    for marker in fatal_markers:
        if marker in body:
            status = "FAIL"
            errors.append(f"Found marker: {marker}")

    return {
        "name": "arena_systems_audit",
        "status": status,
        "error": "; ".join(errors) if errors else None,
        "logs": [f"report: {REPORT}", body[-6000:]],
    }


if __name__ == "__main__":
    main()
