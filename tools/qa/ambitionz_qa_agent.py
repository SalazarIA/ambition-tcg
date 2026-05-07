from pathlib import Path
import argparse
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.qa.qa_config import qa_report_path, ensure_qa_dirs
from tools.qa.qa_backend_flow import run_backend_flow
from tools.qa.qa_socket_flow import run_socket_flow
from tools.qa.qa_browser_flow import run_browser_flow
from tools.qa.qa_arena_systems_audit import run_systems_audit
from tools.qa.qa_routes_flow import run_routes_flow
from tools.qa.qa_deck_inventory_flow import run_deck_inventory_flow
from tools.qa.qa_economy_flow import run_economy_flow
from tools.qa.qa_arena_matrix_flow import run_arena_matrix_flow
from tools.qa.qa_production_flow import run_production_flow
from tools.qa.qa_pvp_socket_flow import run_pvp_socket_flow


def format_result(result):
    lines = []

    status = result.get("status")
    name = result.get("name")

    lines.append(f"## {name}")
    lines.append("")
    lines.append(f"Status: **{status}**")
    lines.append("")

    if result.get("error"):
        lines.append(f"Error: `{result['error']}`")
        lines.append("")

    lines.append("```text")
    for log in result.get("logs") or []:
        lines.append(str(log))
    lines.append("```")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Ambitionz QA Agent")
    parser.add_argument("--target", default="local", choices=["local"], help="QA target")
    parser.add_argument("--suite", default="all", choices=["all", "backend", "socket", "browser", "systems", "routes", "deck", "economy", "arena_matrix", "production", "pvp"], help="Suite to run")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080", help="Base URL for browser QA")
    parser.add_argument("--headed", action="store_true", help="Run browser visibly")
    args = parser.parse_args()

    ensure_qa_dirs()

    results = []

    if args.suite in ("all", "backend"):
        results.append(run_backend_flow())

    if args.suite in ("all", "socket"):
        results.append(run_socket_flow())

    if args.suite in ("browser",):
        results.append(run_browser_flow(base_url=args.base_url, headed=args.headed))

    if args.suite in ("all", "systems"):
        results.append(run_systems_audit())

    if args.suite in ("all", "routes"):
        results.append(run_routes_flow())

    if args.suite in ("all", "deck"):
        results.append(run_deck_inventory_flow())

    if args.suite in ("all", "economy"):
        results.append(run_economy_flow())

    if args.suite in ("all", "arena_matrix"):
        results.append(run_arena_matrix_flow())

    if args.suite in ("production",):
        results.append(run_production_flow(base_url=args.base_url or "https://ambitionzgame.com"))

    if args.suite in ("all", "pvp"):
        results.append(run_pvp_socket_flow())

    passed = all(result.get("status") == "PASS" for result in results)

    report_path = qa_report_path("qa_run")

    lines = [
        "# Ambitionz QA Agent Report",
        "",
        f"- Target: `{args.target}`",
        f"- Suite: `{args.suite}`",
        f"- Overall: `{'PASS' if passed else 'FAIL'}`",
        "",
    ]

    for result in results:
        lines.append(format_result(result))

    report_path.write_text("\n".join(lines))

    print("")
    print("=== AMBITIONZ QA AGENT ===")
    print("RESULT:", "PASS" if passed else "FAIL")
    print("REPORT:", report_path)

    for result in results:
        print(f"- {result['name']}: {result['status']}")
        if result.get("error"):
            print(f"  ERROR: {result['error']}")

    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
