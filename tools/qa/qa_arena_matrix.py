from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.qa.qa_arena_matrix_flow import run_arena_matrix_flow


def main():
    result = run_arena_matrix_flow()
    print("=== QA ARENA MATRIX ===")
    for line in result.get("logs") or []:
        print(line)
    if result.get("status") != "PASS":
        raise SystemExit(result.get("error") or "Arena matrix QA failed.")
    print("PASS arena_matrix_flow")


if __name__ == "__main__":
    main()
