from pathlib import Path
import re

files = [
    Path("static/js/game.js"),
    Path("services/match_payloads.py"),
    Path("game/state.py"),
    Path("app.py"),
]

patterns = [
    "game_state_update",
    "hand",
    "field",
    "monster",
    "spell",
    "trap",
    "emit",
]

print("# Arena Sync Audit")
print()

for path in files:
    if not path.exists():
        print("MISSING", path)
        continue

    text = path.read_text(errors="ignore")
    print(f"## {path}")

    for pattern in patterns:
        count = len(re.findall(re.escape(pattern), text, flags=re.IGNORECASE))
        print(f"- {pattern}: {count}")

    print()

print("Recommendation:")
print("- If hand count is 0 in payload files, backend payload needs explicit `hand` export.")
print("- If game.js renders hand but bridge does not, expose state to `window.AmbitionzArenaStateBridge.updateFromState(payload)`.")
