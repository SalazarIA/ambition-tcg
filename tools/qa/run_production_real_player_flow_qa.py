import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASE_URL = "https://ambitionzgame.com"

cmd = [
    sys.executable,
    "tools/qa/qa_production_real_player_flow.py",
    "--base-url",
    BASE_URL,
]

print("=== PRODUCTION REAL PLAYER FLOW QA ===")
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
    print("RESULT=PASS production_real_player_flow")
else:
    print("RESULT=FAIL production_real_player_flow")
    raise SystemExit(result.returncode)
