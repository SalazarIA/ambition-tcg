from pathlib import Path
from datetime import datetime
import re

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = PROJECT_ROOT / "reports" / "qa"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
REPORT = REPORT_DIR / f"ux_review_{STAMP}.md"

FILES = {
    "arena_template": PROJECT_ROOT / "templates" / "arena.html",
    "arena_js": PROJECT_ROOT / "static" / "js" / "arena_clean_v48.js",
    "shop": PROJECT_ROOT / "templates" / "shop.html",
    "deck_builder": PROJECT_ROOT / "templates" / "deck_builder.html",
    "collection": PROJECT_ROOT / "templates" / "collection.html",
    "inventory": PROJECT_ROOT / "templates" / "inventory.html",
    "style": PROJECT_ROOT / "static" / "css" / "style.css",
}


def read(path):
    return path.read_text(errors="ignore") if path.exists() else ""


def has_any(text, terms):
    lower = text.lower()
    return any(term.lower() in lower for term in terms)


def count_any(text, terms):
    lower = text.lower()
    return sum(lower.count(term.lower()) for term in terms)


def issue(priority, area, problem, recommendation):
    return {
        "priority": priority,
        "area": area,
        "problem": problem,
        "recommendation": recommendation,
    }


def audit_arena(files):
    issues = []
    html = files["arena_template"]
    js = files["arena_js"]
    combined = html + "\n" + js

    secondary_start_hidden = "az48-training-hidden-actions" in html

    if "Start Training" in html and "Start</button>" in html and not secondary_start_hidden:
        issues.append(issue(
            "P1",
            "Arena",
            "There are two start-like controls visible: Start Training and Start.",
            "Keep one primary start CTA in training mode or hide/disable the secondary control."
        ))

    if "Ready" in html and "Commit" in html:
        issues.append(issue(
            "P2",
            "Arena",
            "Ready is labeled with Commit, but the game does not clearly explain that Ready resolves the round.",
            "Change microcopy to Ready / Resolve Round or add a one-line helper after card play."
        ))

    if "Playing card..." in js and "action_error" not in js:
        issues.append(issue(
            "P1",
            "Arena",
            "Arena can show Playing card feedback but may not visibly recover on rejected play actions.",
            "Render action_error visibly and clear transient messages after canonical state update."
        ))

    if "az48_play_card" not in js:
        issues.append(issue(
            "P0",
            "Arena",
            "Clean arena does not use az48_play_card.",
            "Use only the canonical AZ48 socket namespace for card play."
        ))

    if "game_state_update" in js:
        issues.append(issue(
            "P2",
            "Arena",
            "Clean arena still listens to legacy game_state_update.",
            "Keep strict schema filtering or remove the legacy listener after migration."
        ))

    if not has_any(combined, ["No playable card", "Press Ready", "Waiting for battle"]):
        issues.append(issue(
            "P1",
            "Arena",
            "Arena may not clearly tell the player what to do when no card can be played.",
            "Add state-specific guidance: choose intent, play one card, then press Ready."
        ))

    return issues


def audit_shop(files):
    issues = []
    html = files["shop"]

    if not html:
        return [issue("P0", "Shop", "shop.html missing.", "Restore shop template.")]

    if "Open Booster" not in html:
        issues.append(issue(
            "P0",
            "Shop",
            "Shop does not expose Open Booster CTA.",
            "Add a visible Open Booster button when the user has enough coins."
        ))

    if "Coins" not in html:
        issues.append(issue(
            "P1",
            "Shop",
            "Shop does not clearly show wallet coins.",
            "Show Coins, Pack Cost, and Cards per pack above the CTA."
        ))

    if "History" not in html:
        issues.append(issue(
            "P2",
            "Shop",
            "Shop has limited continuity after booster opening.",
            "Keep Booster History visible so users trust card acquisition."
        ))

    if count_any(html, ["Coming Later", "Future Pack"]) >= 2:
        issues.append(issue(
            "P2",
            "Shop",
            "Shop shows multiple locked future packs, which can make the product feel unfinished.",
            "Keep future packs, but mark them as roadmap teasers and emphasize the active pack."
        ))

    return issues


def audit_deck(files):
    issues = []
    html = files["deck_builder"]

    if not html:
        return [issue("P0", "Deck Builder", "deck_builder.html missing.", "Restore deck builder template.")]

    if not has_any(html, ["30", "deck", "monster", "spell", "trap"]):
        issues.append(issue(
            "P0",
            "Deck Builder",
            "Deck rules are not visible enough.",
            "Show fixed beta deck rule: 30 cards, 21 monsters, 6 spells, 3 traps."
        ))

    if not has_any(html, ["Auto", "auto-build", "Auto Build"]):
        issues.append(issue(
            "P1",
            "Deck Builder",
            "Deck builder may lack a recovery path for invalid decks.",
            "Expose Auto Build Deck as a rescue CTA."
        ))

    if not has_any(html, ["save", "Save"]):
        issues.append(issue(
            "P1",
            "Deck Builder",
            "Deck builder save action may not be obvious.",
            "Make Save Deck sticky or highly visible near the deck counter."
        ))

    return issues


def audit_collection_inventory(files):
    issues = []
    collection = files["collection"]
    inventory = files["inventory"]

    if not collection:
        issues.append(issue("P1", "Collection", "collection.html missing.", "Restore collection page."))

    if not inventory:
        issues.append(issue("P1", "Inventory", "inventory.html missing.", "Restore inventory page."))

    if collection and not has_any(collection, ["card", "collection", "monster", "spell", "trap"]):
        issues.append(issue(
            "P1",
            "Collection",
            "Collection page may not communicate card ownership clearly.",
            "Show card count, filters by type/element, and deck builder CTA."
        ))

    if inventory and not has_any(inventory, ["inventory", "owned", "cards", "collection"]):
        issues.append(issue(
            "P1",
            "Inventory",
            "Inventory page may not communicate owned assets clearly.",
            "Show ownership summary and route users to Collection/Deck."
        ))

    return issues


def audit_mobile_css(files):
    issues = []
    css = files["style"]
    media_count = len(re.findall(r"@media", css))

    if media_count < 5:
        issues.append(issue(
            "P1",
            "Mobile/Layout",
            "CSS has few responsive media queries.",
            "Add explicit mobile rules for arena, deck builder, shop, collection and onboarding."
        ))

    if "safe-area-inset" not in css:
        issues.append(issue(
            "P2",
            "Mobile/Layout",
            "CSS may not fully account for mobile safe areas.",
            "Use env(safe-area-inset-*) on mobile bottom nav and arena actions."
        ))

    return issues


def build_report():
    files = {key: read(path) for key, path in FILES.items()}

    issues = []
    issues.extend(audit_arena(files))
    issues.extend(audit_shop(files))
    issues.extend(audit_deck(files))
    issues.extend(audit_collection_inventory(files))
    issues.extend(audit_mobile_css(files))

    priority_order = {"P0": 0, "P1": 1, "P2": 2}
    issues.sort(key=lambda item: priority_order.get(item["priority"], 9))

    p0 = [i for i in issues if i["priority"] == "P0"]
    p1 = [i for i in issues if i["priority"] == "P1"]
    p2 = [i for i in issues if i["priority"] == "P2"]

    lines = [
        "# Ambitionz UX Review Agent Report",
        "",
        f"- Generated: {STAMP}",
        f"- Total issues: {len(issues)}",
        f"- P0: {len(p0)}",
        f"- P1: {len(p1)}",
        f"- P2: {len(p2)}",
        "",
        "## Executive Summary",
        "",
        "The QA technical layer is stable. This report focuses on player clarity, progression guidance, and visible product polish.",
        "",
        "## Priority Matrix",
        "",
        "| Priority | Area | Problem | Recommendation |",
        "|---|---|---|---|",
    ]

    for item in issues:
        lines.append(
            f"| {item['priority']} | {item['area']} | {item['problem']} | {item['recommendation']} |"
        )

    lines.extend([
        "",
        "## Suggested Next Build Order",
        "",
    ])

    if p0:
        lines.append("1. Fix P0 issues before adding new features.")
    else:
        lines.append("1. No P0 UX blockers found.")

    if p1:
        lines.append("2. Polish P1 clarity items: arena guidance, deck rescue, shop wallet/CTA, mobile layout.")
    else:
        lines.append("2. No P1 UX clarity blockers found.")

    lines.append("3. Apply P2 polish after the main loop feels stable.")

    REPORT.write_text("\n".join(lines))
    return REPORT, issues


def run_ux_review():
    report, issues = build_report()
    p0 = [i for i in issues if i["priority"] == "P0"]

    return {
        "name": "ux_review",
        "status": "FAIL" if p0 else "PASS",
        "error": f"{len(p0)} P0 UX blockers found" if p0 else None,
        "logs": [
            f"report: {report}",
            f"issues: {len(issues)}",
            "\n".join(
                f"{i['priority']} {i['area']}: {i['problem']} -> {i['recommendation']}"
                for i in issues
            ),
        ],
    }


def main():
    report, issues = build_report()
    print(report)
    print(f"issues={len(issues)}")
    for item in issues:
        print(f"{item['priority']} | {item['area']} | {item['problem']}")


if __name__ == "__main__":
    main()
