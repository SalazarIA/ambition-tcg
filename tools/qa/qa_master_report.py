
from pathlib import Path
from datetime import datetime
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = PROJECT_ROOT / "reports" / "qa"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
REPORT = REPORT_DIR / f"master_qa_report_{STAMP}.md"


LOCAL_SUITES = [
    "backend",
    "socket",
    "systems",
    "routes",
    "deck",
    "economy",
    "arena_matrix",
]


OPTIONAL_SUITES = [
    "browser",
    "production",
]


def run_command(args, timeout=120):
    try:
        result = subprocess.run(
            args,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        return {
            "args": args,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "timeout": False,
        }

    except subprocess.TimeoutExpired as exc:
        return {
            "args": args,
            "returncode": 124,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "timeout": True,
        }


def parse_status(output):
    if "RESULT: PASS" in output:
        return "PASS"

    if "RESULT: FAIL" in output:
        return "FAIL"

    return "UNKNOWN"


def extract_flow_lines(output):
    lines = []

    for line in output.splitlines():
        stripped = line.strip()

        if stripped.startswith("- ") and (": PASS" in stripped or ": FAIL" in stripped):
            lines.append(stripped)

        if "ERROR:" in stripped:
            lines.append(stripped)

    return lines


def classify_priority(suite, status, output):
    if status == "PASS":
        return "OK"

    lower = output.lower()

    if suite in ("backend", "socket", "systems", "arena_matrix"):
        return "P0"

    if "500" in lower or "traceback" in lower or "exception" in lower:
        return "P0"

    if suite in ("routes", "deck", "economy"):
        return "P1"

    if suite in ("browser", "production"):
        return "P1"

    return "P2"


def recommendation_for(suite, status, output):
    if status == "PASS":
        return "No immediate action."

    lower = output.lower()

    if "play_to_field" in lower:
        return "Remove legacy play_to_field. Use az48_play_card only."

    if "card was not removed from hand" in lower:
        return "Fix card play state propagation: frontend event, backend handler, or render update."

    if "playing card" in lower:
        return "Fix stuck UI message after card click; require az48_state response or action_error handling."

    if "missing" in lower and suite == "systems":
        return "Align HTML IDs, frontend event names, backend handlers, and payload schema."

    if suite == "deck":
        return "Fix deck/inventory ownership consistency before gameplay testing."

    if suite == "economy":
        return "Fix ledger/idempotency/booster ownership before progression release."

    if suite == "routes":
        return "Fix HTTP route status, auth redirects, or static asset availability."

    if suite == "production":
        return "Verify Render deploy, cache bust, service worker, and production static assets."

    if suite == "browser":
        return "Inspect screenshots/report; browser QA found user-visible gameplay breakage."

    return "Inspect suite logs and patch the nearest failing contract."


def run_suite(suite, include_optional=False):
    if suite == "browser":
        # Browser QA needs local server runner.
        args = ["python3", "tools/qa/run_local_browser_qa.py"]
        timeout = 240
    elif suite == "production":
        args = [
            "python3",
            "tools/qa/ambitionz_qa_agent.py",
            "--target",
            "local",
            "--suite",
            "production",
            "--base-url",
            "https://ambitionzgame.com",
        ]
        timeout = 90
    else:
        args = [
            "python3",
            "tools/qa/ambitionz_qa_agent.py",
            "--target",
            "local",
            "--suite",
            suite,
        ]
        timeout = 120

    result = run_command(args, timeout=timeout)
    combined = (result["stdout"] or "") + "\n" + (result["stderr"] or "")

    if suite == "browser":
        status = "PASS" if "RESULT=PASS browser_eagle_eye" in combined else "FAIL"
    else:
        status = parse_status(combined)

    priority = classify_priority(suite, status, combined)

    return {
        "suite": suite,
        "status": status,
        "priority": priority,
        "returncode": result["returncode"],
        "timeout": result["timeout"],
        "flow_lines": extract_flow_lines(combined),
        "recommendation": recommendation_for(suite, status, combined),
        "output": combined,
    }


def build_report(include_browser=False, include_production=False):
    suites = list(LOCAL_SUITES)

    if include_browser:
        suites.append("browser")

    if include_production:
        suites.append("production")

    results = []

    for suite in suites:
        print(f"RUN {suite}...")
        results.append(run_suite(suite))

    overall = "PASS" if all(item["status"] == "PASS" for item in results) else "FAIL"

    p0 = [item for item in results if item["priority"] == "P0"]
    p1 = [item for item in results if item["priority"] == "P1"]

    lines = [
        "# Ambitionz Master QA Report",
        "",
        f"- Generated: {STAMP}",
        f"- Overall: **{overall}**",
        f"- P0 Failures: {len(p0)}",
        f"- P1 Failures: {len(p1)}",
        "",
        "## Executive Summary",
        "",
    ]

    if overall == "PASS":
        lines.append("All selected QA suites passed.")
    else:
        lines.append("One or more QA suites failed. Prioritize P0 before gameplay polish.")

    lines.extend([
        "",
        "## Suite Matrix",
        "",
        "| Suite | Status | Priority | Recommendation |",
        "|---|---:|---:|---|",
    ])

    for item in results:
        lines.append(
            f"| {item['suite']} | {item['status']} | {item['priority']} | {item['recommendation']} |"
        )

    lines.extend([
        "",
        "## Failure Priority",
        "",
    ])

    if not p0 and not p1:
        lines.append("No P0/P1 failures detected.")
    else:
        for item in p0 + p1:
            lines.append(f"### {item['priority']} — {item['suite']}")
            lines.append("")
            lines.append(f"- Status: `{item['status']}`")
            lines.append(f"- Recommendation: {item['recommendation']}")
            lines.append("")

            if item["flow_lines"]:
                lines.append("```text")
                lines.extend(item["flow_lines"][:80])
                lines.append("```")
                lines.append("")

    lines.extend([
        "",
        "## Detailed Logs",
        "",
    ])

    for item in results:
        lines.append(f"### {item['suite']}")
        lines.append("")
        lines.append(f"- Status: `{item['status']}`")
        lines.append(f"- Priority: `{item['priority']}`")
        lines.append(f"- Return code: `{item['returncode']}`")
        lines.append(f"- Timeout: `{item['timeout']}`")
        lines.append("")
        lines.append("```text")
        lines.append(item["output"][-12000:])
        lines.append("```")
        lines.append("")

    REPORT.write_text("\n".join(lines))
    return overall, results


def main():
    include_browser = "--browser" in sys.argv
    include_production = "--production" in sys.argv

    overall, results = build_report(
        include_browser=include_browser,
        include_production=include_production,
    )

    print("")
    print("=== MASTER QA RESULT ===")
    print(f"RESULT={overall}")
    print(f"REPORT={REPORT}")

    for item in results:
        print(f"- {item['suite']}: {item['status']} priority={item['priority']}")

    if overall != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
