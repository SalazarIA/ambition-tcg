import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASE_URL = "https://ambitionzgame.com"

cmd = [
    sys.executable,
    "tools/qa/qa_production_booster_collection_deck_flow.py",
    "--base-url",
    BASE_URL,
]

print("=== PRODUCTION BOOSTER COLLECTION DECK QA ===")
print(f"BASE_URL={BASE_URL}")
print("COMMAND=" + " ".join(cmd))
print("")

result = subprocess.run(
    cmd,
    cwd=str(PROJECT_ROOT),
    text=True,
    capture_output=True,
)

print("=== STDOUT ===")
print(result.stdout)

print("")
print("=== STDERR ===")
print(result.stderr)

if result.returncode == 0:
    print("RESULT=PASS production_booster_collection_deck")
else:
    print("RESULT=FAIL production_booster_collection_deck")
    raise SystemExit(result.returncode)
