from pathlib import Path
import re
import shutil
from datetime import datetime

ROOT = Path(".")
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "backups" / f"beta_core_v111_{STAMP}"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

FILES = [
    "app.py",
    "game/state.py",
    "templates/arena.html",
    "templates/how_to_play.html",
    "templates/welcome.html",
    "templates/index.html",
    "templates/privacy.html",
    "templates/terms.html",
    "templates/deck_builder.html",
    "static/js/game.js",
    "capacitor.config.json",
]

def backup(path: Path):
    if path.exists():
        dest = BACKUP_DIR / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)

def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def write(path: Path, content: str):
    path.write_text(content, encoding="utf-8")

def replace(path_str, old, new):
    path = ROOT / path_str
    if not path.exists():
        print(f"SKIP missing {path_str}")
        return
    backup(path)
    content = read(path)
    if old in content:
        content = content.replace(old, new)
        write(path, content)
        print(f"OK replace in {path_str}")
    else:
        print(f"WARN pattern not found in {path_str}: {old[:80]!r}")

def regex_replace(path_str, pattern, repl, count=0, flags=re.S):
    path = ROOT / path_str
    if not path.exists():
        print(f"SKIP missing {path_str}")
        return
    backup(path)
    content = read(path)
    new_content, n = re.subn(pattern, repl, content, count=count, flags=flags)
    if n:
        write(path, new_content)
        print(f"OK regex {n}x in {path_str}")
    else:
        print(f"WARN regex not found in {path_str}: {pattern[:100]!r}")

# 1) Fix wrong set_player_intent signature.
replace(
    "app.py",
    'set_player_intent(player, intent, match.setdefault("logs", []))',
    'set_player_intent(player, intent)'
)

# 2) Safety net: Overreach should not be sent as a normal intent.
# Keep backend resilient: if old frontend/cache sends Overreach, normalize it to Ambition Unleash flow when possible.
regex_replace(
    "app.py",
    r'(def set_intent\(data\):\n(?:    .*\n){0,30}?    intent = data\.get\("intent"\)\n)',
    r'\1    if intent == "Overreach":\n        intent = "Ambition Unleash"\n',
    count=1,
    flags=0
)

# 3) Normalize UI language from Overreach intent to Ambition Unleash.
# This is intentional: Overreach remains a lore word, but the clickable mechanic should be explicit.
ui_files = [
    "templates/arena.html",
    "templates/how_to_play.html",
    "templates/welcome.html",
    "templates/index.html",
    "static/js/game.js",
]
for f in ui_files:
    path = ROOT / f
    if not path.exists():
        print(f"SKIP missing {f}")
        continue
    backup(path)
    c = read(path)
    c = c.replace("Strike, Guard, Focus or Overreach", "Strike, Guard, Focus or Ambition Unleash")
    c = c.replace("Strike, Guard, Focus and Overreach", "Strike, Guard, Focus and Ambition Unleash")
    c = c.replace("Risk. Elements. Overreach.", "Risk. Elements. Ambition.")
    c = c.replace("Overreach is strongest when you already have pressure.", "Ambition Unleash is strongest when you already have pressure and 5 Ambition.")
    c = c.replace("Overreach change how each round resolves.", "Ambition Unleash changes how a decisive round resolves.")
    c = c.replace("Overreach define the clash.", "Ambition Unleash defines the decisive clash.")
    c = c.replace("Overreach selected. Commit only when the reward is worth the exposure.", "Ambition Unleash selected. Commit only when the reward is worth the exposure.")
    c = c.replace("Overreach armed: high pressure, high risk.", "Ambition Unleash armed: high pressure, high risk.")
    c = c.replace('data-intent="Overreach">Overreach</button>', 'data-intent="Ambition Unleash">Ambition Unleash</button>')
    c = c.replace('selectedIntent === "Overreach"', 'selectedIntent === "Ambition Unleash"')
    c = c.replace('button.dataset.intent === "Overreach"', 'button.dataset.intent === "Ambition Unleash"')
    write(path, c)
    print(f"OK normalized Overreach UI in {f}")

# 4) Fix duplicate const cost in deck_builder.html.
path = ROOT / "templates/deck_builder.html"
if path.exists():
    backup(path)
    c = read(path)

    # The common broken shape has two const cost declarations close together.
    # Rename only the second occurrence inside the same JS area to avoid redeclaration.
    first = c.find('const cost = document.getElementById("filter-cost") ? document.getElementById("filter-cost").value : "";')
    second = c.find('const cost = document.getElementById("filter-cost").value;', first + 1)

    if second != -1:
        c = c[:second] + c[second:].replace(
            'const cost = document.getElementById("filter-cost").value;',
            'const selectedCost = document.getElementById("filter-cost").value;',
            1
        )
        # If the second value is used immediately in comparisons, keep compatibility.
        # This avoids breaking existing code that expects `cost` later.
        insert_at = c.find('const selectedCost = document.getElementById("filter-cost").value;')
        line_end = c.find("\n", insert_at)
        if insert_at != -1 and line_end != -1 and "const costForFilter = selectedCost;" not in c[insert_at:line_end+80]:
            c = c[:line_end+1] + '            const costForFilter = selectedCost;\n' + c[line_end+1:]

        # Try to update common filter comparison references after the second declaration.
        tail_start = c.find('const selectedCost = document.getElementById("filter-cost").value;')
        if tail_start != -1:
            head = c[:tail_start]
            tail = c[tail_start:]
            tail = tail.replace("filter-cost", "filter-cost")
            tail = re.sub(r'(\bcardCost\b\s*!==\s*)cost\b', r'\1costForFilter', tail)
            tail = re.sub(r'(\bcost\b\s*&&)', r'costForFilter &&', tail, count=1)
            tail = re.sub(r'(\bString\([^)]*cost[^)]*\)\s*!==\s*)cost\b', r'\1costForFilter', tail)
            c = head + tail

        write(path, c)
        print("OK fixed duplicate const cost in templates/deck_builder.html")
    else:
        print("WARN duplicate const cost pattern not found exactly in templates/deck_builder.html")
else:
    print("SKIP missing templates/deck_builder.html")

# 5) Standardize legal URLs to current production Render URL.
for f in ["templates/privacy.html", "templates/terms.html"]:
    path = ROOT / f
    if path.exists():
        backup(path)
        c = read(path)
        c = c.replace("https://ambitionzgame.com", "https://ambition-tcg.onrender.com")
        write(path, c)
        print(f"OK standardized production URL in {f}")

# 6) Standardize apple mobile web app title from Ambition to Ambitionz.
for f in ["templates/collection.html", "templates/deck_builder.html", "templates/missions.html", "templates/offline.html", "templates/progression.html", "templates/shop.html"]:
    path = ROOT / f
    if path.exists():
        backup(path)
        c = read(path)
        c = c.replace('content="Ambition"', 'content="Ambitionz"')
        write(path, c)
        print(f"OK standardized mobile title in {f}")

print(f"\nBackup created at: {BACKUP_DIR}")
