
from pathlib import Path
from datetime import datetime
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = PROJECT_ROOT / "reports" / "qa"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
REPORT = REPORT_DIR / f"master_qa_report_{STAMP}.md"

CORE_SUITES = [
    "backend",
    "socket",
    "systems",
    "routes",
    "deck",
    "economy",
    "arena_matrix",
    "pvp",
]

BROWSER_RUNNERS = {
    "browser": "tools/qa/run_local_browser_qa.py",
    "browser_full_match": "tools/qa/run_browser_full_match_qa.py",
    "browser_viewports": "tools/qa/run_browser_viewports_qa.py",
    "browser_shop_deck": "tools/qa/run_browser_shop_deck_qa.py",
    "rebirth_visual": "tools/qa/qa_rebirth_visual_screenshots.py",
}


def run_command(args, timeout=180):
    try:
        result = subprocess.run(
            args,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        return {
            "returncode": result.returncode,
            "stdout": result.stdout or "",
            "stderr": result.stderr or "",
            "timeout": False,
        }

    except subprocess.TimeoutExpired as exc:
        return {
            "returncode": 124,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "timeout": True,
        }

    except Exception as exc:
        return {
            "returncode": 1,
            "stdout": "",
            "stderr": f"{type(exc).__name__}: {exc}",
            "timeout": False,
        }


def parse_agent_status(output):
    if "RESULT: PASS" in output:
        return "PASS"

    if "RESULT: FAIL" in output:
        return "FAIL"

    return "UNKNOWN"


def parse_runner_status(suite, output):
    markers = {
        "browser": "RESULT=PASS browser_eagle_eye",
        "browser_full_match": "RESULT=PASS browser_full_match",
        "browser_viewports": "RESULT=PASS browser_viewports",
        "browser_shop_deck": "RESULT=PASS browser_shop_deck",
        "rebirth_visual": "RESULT=PASS rebirth_visual_screenshots",
    }

    marker = markers.get(suite)

    if marker and marker in output:
        return "PASS"

    if "RESULT=FAIL" in output or "Traceback" in output:
        return "FAIL"

    return "UNKNOWN"


def priority_for(suite, status, output):
    if status == "PASS":
        return "OK"

    if status == "SKIP":
        return "SKIP"

    lower = output.lower()

    if suite in ("backend", "socket", "systems", "arena_matrix", "pvp"):
        return "P0"

    if "traceback" in lower or "internal server error" in lower or "500" in lower:
        return "P0"

    if suite in ("routes", "deck", "economy", "production"):
        return "P1"

    if suite.startswith("browser"):
        return "P1"

    return "P2"


def recommendation_for(suite, status, output):
    if status == "PASS":
        return "No immediate action."

    if status == "SKIP":
        return "Runner not found; create or commit the missing QA runner."

    lower = output.lower()

    if "card was not removed from hand" in lower or "did not mutate hand" in lower:
        return "Fix card play event/state/render propagation."

    if "playing card" in lower:
        return "Fix stuck Playing card UI state and require az48_state/action_error handling."

    if "play_to_field" in lower:
        return "Remove legacy play_to_field and use az48_play_card."

    if "module not found" in lower:
        return "Fix missing QA module import or create the expected file."

    if "argument --target" in lower or "invalid choice" in lower:
        return "Fix qa_agent argparse target/suite configuration."

    if "integrityerror" in lower:
        return "Fix QA fixture creation or database required fields."

    if suite == "production":
        return "Check deploy/cache/static assets on production."

    if suite.startswith("browser"):
        return "Inspect browser screenshots and visible state regression."

    return "Inspect suite report and fix the nearest failing contract."


def flow_lines(output):
    lines = []

    for line in output.splitlines():
        s = line.strip()

        if s.startswith("- ") and (": PASS" in s or ": FAIL" in s):
            lines.append(s)

        if "ERROR:" in s:
            lines.append(s)

        if "RESULT=" in s or "RESULT:" in s:
            lines.append(s)

    return lines[:100]


def run_agent_suite(suite):
    args = [
        "python3",
        "tools/qa/ambitionz_qa_agent.py",
        "--target",
        "local",
        "--suite",
        suite,
    ]

    result = run_command(args, timeout=180)
    output = result["stdout"] + "\n" + result["stderr"]
    status = parse_agent_status(output)

    return {
        "suite": suite,
        "status": status,
        "priority": priority_for(suite, status, output),
        "recommendation": recommendation_for(suite, status, output),
        "returncode": result["returncode"],
        "timeout": result["timeout"],
        "output": output,
        "flow_lines": flow_lines(output),
    }


def run_browser_runner(suite):
    runner = BROWSER_RUNNERS[suite]
    runner_path = PROJECT_ROOT / runner

    if not runner_path.exists():
        output = f"Missing runner: {runner}"
        return {
            "suite": suite,
            "status": "SKIP",
            "priority": "SKIP",
            "recommendation": recommendation_for(suite, "SKIP", output),
            "returncode": 0,
            "timeout": False,
            "output": output,
            "flow_lines": [output],
        }

    result = run_command(["python3", runner], timeout=360)
    output = result["stdout"] + "\n" + result["stderr"]
    status = parse_runner_status(suite, output)

    return {
        "suite": suite,
        "status": status,
        "priority": priority_for(suite, status, output),
        "recommendation": recommendation_for(suite, status, output),
        "returncode": result["returncode"],
        "timeout": result["timeout"],
        "output": output,
        "flow_lines": flow_lines(output),
    }


def run_production(base_url="https://ambitionzgame.com"):
    args = [
        "python3",
        "tools/qa/ambitionz_qa_agent.py",
        "--target",
        "local",
        "--suite",
        "production",
        "--base-url",
        base_url,
    ]

    result = run_command(args, timeout=120)
    output = result["stdout"] + "\n" + result["stderr"]
    status = parse_agent_status(output)

    return {
        "suite": "production",
        "status": status,
        "priority": priority_for("production", status, output),
        "recommendation": recommendation_for("production", status, output),
        "returncode": result["returncode"],
        "timeout": result["timeout"],
        "output": output,
        "flow_lines": flow_lines(output),
    }


def build_report(include_browser=False, include_deep_browser=False, include_production=False):
    results = []

    for suite in CORE_SUITES:
        print(f"RUN {suite}...")
        results.append(run_agent_suite(suite))

    if include_browser:
        print("RUN browser...")
        results.append(run_browser_runner("browser"))

    if include_deep_browser:
        for suite in ["browser_full_match", "browser_viewports", "browser_shop_deck", "rebirth_visual"]:
            print(f"RUN {suite}...")
            results.append(run_browser_runner(suite))

    if include_production:
        print("RUN production...")
        results.append(run_production())

    hard_failures = [
        r for r in results
        if r["status"] not in ("PASS", "SKIP")
    ]

    overall = "PASS" if not hard_failures else "FAIL"

    p0 = [r for r in results if r["priority"] == "P0"]
    p1 = [r for r in results if r["priority"] == "P1"]
    skipped = [r for r in results if r["status"] == "SKIP"]

    lines = [
        "# Ambitionz Master QA Report",
        "",
        f"- Generated: {STAMP}",
        f"- Overall: **{overall}**",
        f"- P0 failures: {len(p0)}",
        f"- P1 failures: {len(p1)}",
        f"- Skipped optional suites: {len(skipped)}",
        "",
        "## Suite Matrix",
        "",
        "| Suite | Status | Priority | Recommendation |",
        "|---|---:|---:|---|",
    ]

    for r in results:
        lines.append(f"| {r['suite']} | {r['status']} | {r['priority']} | {r['recommendation']} |")

    lines.extend([
        "",
        "## P0/P1 Focus",
        "",
    ])

    focus = p0 + p1

    if not focus:
        lines.append("No P0/P1 failures detected.")
    else:
        for r in focus:
            lines.extend([
                f"### {r['priority']} — {r['suite']}",
                "",
                f"- Status: `{r['status']}`",
                f"- Recommendation: {r['recommendation']}",
                "",
                "```text",
                "\n".join(r["flow_lines"]),
                "```",
                "",
            ])

    if skipped:
        lines.extend([
            "",
            "## Skipped Optional Suites",
            "",
        ])

        for r in skipped:
            lines.append(f"- `{r['suite']}`: {r['recommendation']}")

    lines.extend([
        "",
        "## Detailed Logs",
        "",
    ])

    for r in results:
        lines.extend([
            f"### {r['suite']}",
            "",
            f"- Status: `{r['status']}`",
            f"- Priority: `{r['priority']}`",
            f"- Return code: `{r['returncode']}`",
            f"- Timeout: `{r['timeout']}`",
            "",
            "```text",
            r["output"][-14000:],
            "```",
            "",
        ])

    REPORT.write_text("\n".join(lines))
    return overall, results


def main():
    include_browser = "--browser" in sys.argv
    include_deep_browser = "--deep-browser" in sys.argv or "--full" in sys.argv
    include_production = "--production" in sys.argv or "--full" in sys.argv

    overall, results = build_report(
        include_browser=include_browser,
        include_deep_browser=include_deep_browser,
        include_production=include_production,
    )

    print("")
    print("=== MASTER QA RESULT ===")
    print(f"RESULT={overall}")
    print(f"REPORT={REPORT}")

    for r in results:
        print(f"- {r['suite']}: {r['status']} priority={r['priority']}")

    if overall != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
