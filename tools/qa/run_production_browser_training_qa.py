import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE_URL = "https://ambitionzgame.com"

cmd = [
    sys.executable,
    "tools/qa/ambitionz_qa_agent.py",
    "--target",
    "local",
    "--suite",
    "browser_full_match",
    "--base-url",
    BASE_URL,
]

print("=== PRODUCTION BROWSER TRAINING QA ===")
print("BASE_URL=" + BASE_URL)
print("COMMAND=" + " ".join(cmd))

result = subprocess.run(
    cmd,
    cwd=ROOT,
    text=True,
    capture_output=True,
    timeout=180,
)

print("")
print("=== STDOUT ===")
print(result.stdout)

print("")
print("=== STDERR ===")
print(result.stderr)

if result.returncode == 0:
    print("RESULT=PASS production_browser_training")
else:
    print("RESULT=FAIL production_browser_training")
    raise SystemExit(result.returncode)
