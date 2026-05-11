from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.qa.qa_backend_flow import run_backend_flow


def main():
    result = run_backend_flow()
    print("=== QA BACKEND ===")
    for line in result.get("logs") or []:
        print(line)
    if result.get("status") != "PASS":
        raise SystemExit(result.get("error") or "Backend QA failed.")
    print("PASS backend_training_flow")


if __name__ == "__main__":
    main()
