
from pathlib import Path
from datetime import datetime
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

REPORT_DIR = PROJECT_ROOT / "reports" / "qa"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
REPORT = REPORT_DIR / f"arena_systems_audit_{STAMP}.md"


def read(path):
    p = PROJECT_ROOT / path
    return p.read_text(errors="ignore") if p.exists() else ""


def code_block(text):
    return "```text\n" + str(text).strip() + "\n```"


def extract_js_function(text, function_name):
    needle = f"function {function_name}("
    start = text.find(needle)

    if start < 0:
        return ""

    brace_start = text.find("{", start)
    if brace_start < 0:
        return ""

    depth = 0

    for index in range(brace_start, len(text)):
        char = text[index]

        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1

            if depth == 0:
                return text[start:index + 1]

    return text[start:]


def find_lines(text, patterns, limit=160):
    out = []

    for line_no, line in enumerate(text.splitlines(), start=1):
        if any(pattern in line for pattern in patterns):
            out.append(f"{line_no}: {line}")

        if len(out) >= limit:
            break

    return out


def add_section(lines, title):
    lines.append("")
    lines.append(f"## {title}")
    lines.append("")


def audit_contract(lines, template, arena_js, app):
    add_section(lines, "1. Contract Audit")

    dom_ids = [
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

    events = [
        "az48_start_training",
        "az48_set_intent",
        "az48_play_card",
        "az48_declare_ready",
        "az48_state",
    ]

    lines.append("### DOM IDs")
    lines.append(code_block("\n".join(
        f"- {dom_id}: {'OK' if dom_id in template else 'MISSING'}"
        for dom_id in dom_ids
    )))

    lines.append("")
    lines.append("### Socket/Event Contract")
    lines.append(code_block("\n".join(
        f"- {event}: JS={'OK' if event in arena_js else 'MISSING'} | backend={'OK' if event in app else 'MISSING'}"
        for event in events
    )))


def audit_legacy(lines, template, arena_js, app):
    add_section(lines, "2. Legacy Conflict Audit")

    terms = [
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
    for term in terms:
        count = template.count(term) + arena_js.count(term) + app.count(term)
        if count:
            findings.append(f"- {term}: {count}")

    if not findings:
        findings.append("No legacy conflict terms found.")

    lines.append(code_block("\n".join(findings)))

    play_card_body = extract_js_function(arena_js, "playCard")

    risks = []

    if "play_to_field" in arena_js:
        risks.append("P0: clean arena JS still references legacy play_to_field.")
    if "c.id" in play_card_body:
        risks.append("P0: playCard references c.id; use id/card_id instead.")
    if "emit(\"declare_ready\"" in arena_js:
        risks.append("P1: clean arena emits legacy declare_ready.")
    if "emit(\"choose_intent\"" in arena_js:
        risks.append("P1: clean arena emits legacy choose_intent.")
    if "game_state_update" in arena_js and "ambitionz_arena_clean_v50" not in arena_js:
        risks.append("P1: game_state_update listener lacks strict clean schema filter.")
    if "game.js" in template and "arena_clean_v48.js" in template:
        risks.append("P0: template loads game.js and clean arena together.")
    if "arena_app.js" in template and "arena_clean_v48.js" in template:
        risks.append("P0: template loads arena_app.js and clean arena together.")

    if not risks:
        risks.append("No P0/P1 legacy renderer risk detected.")

    lines.append("")
    lines.append("### Risk Summary")
    lines.append(code_block("\n".join(risks)))


def audit_play_card(lines, arena_js):
    add_section(lines, "3. Play Card Function Audit")

    body = extract_js_function(arena_js, "playCard")

    if not body:
        lines.append(code_block("P0: function playCard(id) not found."))
        return

    lines.append(code_block(body[:3500]))

    checks = [
        ("Uses az48_play_card", "az48_play_card" in body),
        ("Does not use play_to_field", "play_to_field" not in body),
        ("Does not use undefined c.id", "c.id" not in body),
        ("Sends card_id from id", "card_id: id" in body),
        ("Sends card_index", "card_index" in body),
    ]

    lines.append("")
    lines.append("### Assertions")
    lines.append(code_block("\n".join(
        f"- {name}: {'OK' if ok else 'FAIL'}"
        for name, ok in checks
    )))


def audit_backend(lines, app):
    add_section(lines, "4. Backend Handler Audit")

    patterns = [
        '@socketio.on("az48_start_training")',
        '@socketio.on("az48_request_state")',
        '@socketio.on("az48_set_intent")',
        '@socketio.on("az48_play_card")',
        '@socketio.on("az48_declare_ready")',
        "def emit_az48_state_for_sid",
        "build_arena_clean_state",
    ]

    lines.append(code_block("\n".join(
        f"- {pattern}: {'OK' if pattern in app else 'MISSING'}"
        for pattern in patterns
    )))

    lines.append("")
    lines.append("### Relevant Lines")
    lines.append(code_block("\n".join(find_lines(app, [
        "az48_start_training",
        "az48_set_intent",
        "az48_play_card",
        "az48_declare_ready",
        "emit_az48_state_for_sid",
        "build_arena_clean_state",
    ]))))


def audit_state(lines, arena_state, match_actions):
    add_section(lines, "5. State Architecture Audit")

    checks = [
        ("arena_clean_state has build_arena_clean_state", "def build_arena_clean_state" in arena_state),
        ("arena_clean_state includes legal_actions", "legal_actions" in arena_state),
        ("arena_clean_state includes playable_card_ids", "playable_card_ids" in arena_state),
        ("match_actions has play_card", "def play_card" in match_actions),
        ("match_actions mutates hand", ".pop(" in match_actions and "hand" in match_actions),
        ("match_actions has declare_ready", "def declare_ready" in match_actions),
        ("match_actions references round/resolve", "round" in match_actions.lower() or "resolve" in match_actions.lower()),
    ]

    lines.append(code_block("\n".join(
        f"- {name}: {'OK' if ok else 'CHECK'}"
        for name, ok in checks
    )))


def audit_recommendations(lines, template, arena_js, app):
    add_section(lines, "6. Engineering Recommendations")

    play_card_body = extract_js_function(arena_js, "playCard")
    recs = []

    if "play_to_field" in arena_js:
        recs.append("P0: Remove play_to_field from clean arena.")
    if "c.id" in play_card_body:
        recs.append("P0: Fix playCard c.id usage.")
    if "az48-hand" not in template:
        recs.append("P0: Add #az48-hand to arena template.")
    if "az48-ready" not in template:
        recs.append("P0: Add #az48-ready to arena template.")
    if "az48_play_card" not in app:
        recs.append("P0: Add backend az48_play_card handler.")

    recs.extend([
        "Architecture target: one arena renderer, one payload schema, one event namespace.",
        "Clean arena should prefer az48_state and ignore incompatible legacy payloads.",
        "Browser QA must verify hand decreases, field increases, round/HP changes, and no stuck message.",
        "Production QA must verify cache version after deploy.",
    ])

    lines.append(code_block("\n".join(f"- {rec}" for rec in recs)))


def build_report():
    template = read("templates/arena.html")
    arena_js = read("static/js/arena_clean_v48.js")
    app = read("app.py")
    arena_state = read("services/arena_clean_state.py")
    match_actions = read("services/match_actions_v1.py")

    lines = [
        "# Ambitionz Arena Systems Audit",
        "",
        f"- Generated: {STAMP}",
    ]

    audit_contract(lines, template, arena_js, app)
    audit_legacy(lines, template, arena_js, app)
    audit_play_card(lines, arena_js)
    audit_backend(lines, app)
    audit_state(lines, arena_state, match_actions)
    audit_recommendations(lines, template, arena_js, app)

    body = "\n".join(lines)
    REPORT.write_text(body)
    return body


def run_systems_audit():
    body = build_report()

    fail_markers = [
        "P0:",
        "MISSING",
        "FAIL",
        "function playCard(id) not found",
    ]

    errors = [marker for marker in fail_markers if marker in body]
    status = "FAIL" if errors else "PASS"

    return {
        "name": "arena_systems_audit",
        "status": status,
        "error": "; ".join(f"Found marker: {marker}" for marker in errors) if errors else None,
        "logs": [
            f"report: {REPORT}",
            body[-7000:],
        ],
    }


def main():
    build_report()
    print(REPORT)


if __name__ == "__main__":
    main()
