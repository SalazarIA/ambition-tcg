"""Playwright UI auditor for Ambitionz Rebirth.

The script is intentionally standalone so it can audit production Render or a
local server without importing the Flask app. It writes screenshots and logs to
static/img/debug by default.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


DEFAULT_BASE_URL = "https://ambition-tcg.onrender.com"
DEFAULT_DEBUG_DIR = Path("static/img/debug")
DEFAULT_TIMEOUT_MS = 20_000

VIEWPORTS = {
    "desktop": {"width": 1440, "height": 1000, "is_mobile": False},
    "mobile390": {"width": 390, "height": 844, "is_mobile": True},
}

NAV_STEPS = [
    {"name": "home", "selector": ".rb-global-brand[href]", "expected_path": "/"},
    {"name": "arena", "selector": '.rb-global-tabs a[href="/rebirth"]', "expected_path": "/rebirth"},
    {"name": "shop", "selector": '.rb-global-tabs a[href="/rebirth/shop"]', "expected_path": "/rebirth/shop"},
]


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def normalize_base_url(value: str) -> str:
    url = (value or DEFAULT_BASE_URL).strip()
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return url.rstrip("/")


def same_origin_url(base_url: str, path: str) -> str:
    return urljoin(f"{base_url}/", path.lstrip("/"))


def safe_wait(page: Page, state: str = "networkidle", timeout: int = DEFAULT_TIMEOUT_MS) -> None:
    try:
        page.wait_for_load_state(state, timeout=timeout)
    except PlaywrightTimeoutError:
        try:
            page.wait_for_load_state("domcontentloaded", timeout=5_000)
        except PlaywrightTimeoutError:
            pass


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True), encoding="utf-8")


def append_jsonl(path: Path, items: List[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for item in items:
            handle.write(json.dumps(item, ensure_ascii=True, sort_keys=True) + "\n")


def route_path(page: Page) -> str:
    parsed = urlparse(page.url)
    return parsed.path or "/"


def severity_for_event(event: Dict[str, Any]) -> Optional[str]:
    event_type = event.get("event_type")
    text = f"{event.get('text', '')} {event.get('url', '')}".lower()
    status = int(event.get("status", 0) or 0)
    if event_type == "pageerror":
        return "high"
    if event_type == "requestfailed":
        failure = str(event.get("failure") or "")
        if event.get("resource_type") == "image" and "ERR_ABORTED" in failure:
            return None
        return "high"
    if status >= 500:
        return "high"
    if status in {404, 410}:
        return "medium"
    if event.get("type") == "error":
        return "high"
    if event.get("type") == "warning" and any(token in text for token in ["404", "failed", "error", "blocked"]):
        return "medium"
    return None


def bind_observers(page: Page, events: List[Dict[str, Any]]) -> None:
    def push(payload: Dict[str, Any]) -> None:
        payload.setdefault("page_url", page.url)
        payload.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        severity = severity_for_event(payload)
        if severity:
            payload["severity"] = severity
        events.append(payload)

    page.on(
        "console",
        lambda message: push(
            {
                "event_type": "console",
                "type": message.type,
                "text": message.text,
                "location": message.location,
            }
        ),
    )
    page.on(
        "pageerror",
        lambda error: push({"event_type": "pageerror", "text": str(error)}),
    )
    page.on(
        "requestfailed",
        lambda request: push(
            {
                "event_type": "requestfailed",
                "method": request.method,
                "url": request.url,
                "resource_type": request.resource_type,
                "failure": request.failure,
            }
        ),
    )
    page.on(
        "response",
        lambda response: (
            push(
                {
                    "event_type": "response",
                    "status": response.status,
                    "url": response.url,
                    "resource_type": response.request.resource_type,
                }
            )
            if response.status >= 400
            else None
        ),
    )


def collect_dom_metrics(page: Page) -> Dict[str, Any]:
    return page.evaluate(
        """
        () => {
            const number = (value) => Math.round(Number(value || 0) * 100) / 100;
            const rectPayload = (el) => {
                const rect = el.getBoundingClientRect();
                return {
                    x: number(rect.x),
                    y: number(rect.y),
                    width: number(rect.width),
                    height: number(rect.height),
                    ratio: rect.height ? number(rect.width / rect.height) : null
                };
            };
            const visible = (el) => {
                const style = getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                return style.visibility !== "hidden" && style.display !== "none" && rect.width > 0 && rect.height > 0;
            };
            const navLinks = Array.from(document.querySelectorAll(".rb-global-brand, .rb-global-tabs a")).map((el) => ({
                text: (el.textContent || "").replace(/\\s+/g, " ").trim(),
                href: el.getAttribute("href"),
                visible: visible(el),
                rect: rectPayload(el)
            }));
            const imageNodes = Array.from(document.querySelectorAll([
                ".rb-card-art img",
                ".rb-product-card img",
                ".rb-loadout-row img",
                ".rb-tcg-card img"
            ].join(","))).slice(0, 80).map((el) => {
                const style = getComputedStyle(el);
                return {
                    selector: el.className || el.tagName.toLowerCase(),
                    src: el.currentSrc || el.src || "",
                    objectFit: style.objectFit,
                    objectPosition: style.objectPosition,
                    naturalWidth: el.naturalWidth || 0,
                    naturalHeight: el.naturalHeight || 0,
                    complete: Boolean(el.complete),
                    rect: rectPayload(el)
                };
            });
            const bgLayers = Array.from(document.querySelectorAll(".rb-card-image-layer, .rb-card-art, .rb-mini-art, .rb-field-art")).slice(0, 120).map((el) => {
                const style = getComputedStyle(el);
                return {
                    selector: Array.from(el.classList).join("."),
                    backgroundSize: style.backgroundSize,
                    backgroundPosition: style.backgroundPosition,
                    backgroundRepeat: style.backgroundRepeat,
                    rect: rectPayload(el)
                };
            });
            const tcgCards = Array.from(document.querySelectorAll(".rb-tcg-card, .rb-mini-card, .rb-field-card, .rb-product-card")).slice(0, 100).map((el) => {
                const style = getComputedStyle(el);
                return {
                    selector: Array.from(el.classList).join("."),
                    visible: visible(el),
                    overflow: style.overflow,
                    rect: rectPayload(el)
                };
            });
            const fieldSlots = Array.from(document.querySelectorAll(".rb-field-slots")).map((el) => {
                const style = getComputedStyle(el);
                const columns = style.gridTemplateColumns.split(" ").filter(Boolean);
                return {
                    id: el.id,
                    columns: columns.length,
                    gridTemplateColumns: style.gridTemplateColumns,
                    children: el.children.length,
                    rect: rectPayload(el)
                };
            });
            const brokenImages = Array.from(document.images).filter((img) => img.complete && img.naturalWidth === 0).map((img) => img.currentSrc || img.src);
            return {
                title: document.title,
                url: location.href,
                path: location.pathname,
                viewport: {
                    width: window.innerWidth,
                    height: window.innerHeight,
                    devicePixelRatio: window.devicePixelRatio
                },
                scroll: {
                    documentWidth: document.documentElement.scrollWidth,
                    viewportWidth: document.documentElement.clientWidth,
                    horizontalOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth
                },
                navLinks,
                imageNodes,
                bgLayers,
                tcgCards,
                fieldSlots,
                brokenImages,
                frameworkOverlay: Boolean(document.querySelector("[data-nextjs-dialog-overlay], vite-error-overlay, .webpack-dev-server-client-overlay"))
            };
        }
        """
    )


def analyze_metrics(metrics: Dict[str, Any], step_name: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    nav_by_href = {item.get("href"): item for item in metrics.get("navLinks", [])}
    for href in ["/", "/rebirth", "/rebirth/shop"]:
        item = nav_by_href.get(href)
        if not item:
            findings.append(
                {
                    "severity": "high",
                    "step": step_name,
                    "kind": "navbar",
                    "message": f"Navbar link missing: {href}",
                }
            )
        elif not item.get("visible"):
            findings.append(
                {
                    "severity": "high",
                    "step": step_name,
                    "kind": "navbar",
                    "message": f"Navbar link is not visible: {href}",
                    "rect": item.get("rect"),
                }
            )
    for image in metrics.get("imageNodes", []):
        if image.get("objectFit") == "cover":
            findings.append(
                {
                    "severity": "medium",
                    "step": step_name,
                    "kind": "image-fit",
                    "message": "Image element still uses object-fit: cover.",
                    "image": image,
                }
            )
        if image.get("complete") and not image.get("naturalWidth"):
            findings.append(
                {
                    "severity": "high",
                    "step": step_name,
                    "kind": "broken-image",
                    "message": "Image completed with naturalWidth=0.",
                    "image": image,
                }
            )
    for layer in metrics.get("bgLayers", []):
        if layer.get("backgroundSize") == "cover":
            findings.append(
                {
                    "severity": "medium",
                    "step": step_name,
                    "kind": "background-fit",
                    "message": "Card background layer still uses background-size: cover.",
                    "layer": layer,
                }
            )
    for slot in metrics.get("fieldSlots", []):
        if slot.get("columns") != 3:
            findings.append(
                {
                    "severity": "high",
                    "step": step_name,
                    "kind": "field-grid",
                    "message": f"Battlefield grid has {slot.get('columns')} columns instead of 3.",
                    "slot": slot,
                }
            )
    if metrics.get("scroll", {}).get("horizontalOverflow", 0) > 2:
        findings.append(
            {
                "severity": "medium",
                "step": step_name,
                "kind": "overflow",
                "message": "Page has horizontal overflow.",
                "scroll": metrics.get("scroll"),
            }
        )
    if metrics.get("frameworkOverlay"):
        findings.append(
            {
                "severity": "high",
                "step": step_name,
                "kind": "framework-overlay",
                "message": "Framework error overlay detected.",
            }
        )
    return findings


def screenshot(page: Page, debug_dir: Path, stamp: str, viewport_name: str, step_name: str) -> str:
    path = debug_dir / f"{stamp}_{viewport_name}_{step_name}.png"
    page.screenshot(path=str(path), full_page=True)
    return str(path)


def capture_step(
    page: Page,
    debug_dir: Path,
    stamp: str,
    viewport_name: str,
    step_name: str,
) -> Dict[str, Any]:
    safe_wait(page)
    last_error: Optional[Exception] = None
    for _attempt in range(3):
        try:
            metrics = collect_dom_metrics(page)
            break
        except PlaywrightError as exc:
            last_error = exc
            if "Execution context was destroyed" not in str(exc):
                raise
            safe_wait(page, state="domcontentloaded", timeout=8_000)
    else:
        raise last_error or RuntimeError("Failed to collect DOM metrics.")
    shot = screenshot(page, debug_dir, stamp, viewport_name, step_name)
    return {
        "name": step_name,
        "url": page.url,
        "path": route_path(page),
        "screenshot": shot,
        "metrics": metrics,
        "findings": analyze_metrics(metrics, f"{viewport_name}:{step_name}"),
    }


def attempt_login(page: Page, args: argparse.Namespace, audit_notes: List[Dict[str, Any]]) -> None:
    email = args.login_email or os.environ.get("UI_AUDITOR_EMAIL")
    password = args.login_password or os.environ.get("UI_AUDITOR_PASSWORD")
    if args.skip_login:
        audit_notes.append({"kind": "auth", "status": "skipped", "reason": "--skip-login supplied"})
        return
    if not email or not password:
        audit_notes.append(
            {
                "kind": "auth",
                "status": "skipped",
                "reason": "UI_AUDITOR_EMAIL and UI_AUDITOR_PASSWORD are not set.",
            }
        )
        return
    try:
        page.locator("[data-rebirth-auth-open]").first.click(timeout=5_000)
        page.locator("[data-rebirth-login] input[name='email']").fill(email, timeout=5_000)
        page.locator("[data-rebirth-login] input[name='password']").fill(password, timeout=5_000)
        page.locator("[data-rebirth-login] button[type='submit']").click(timeout=5_000)
        safe_wait(page)
        audit_notes.append({"kind": "auth", "status": "attempted", "current_url": page.url})
    except PlaywrightError as exc:
        audit_notes.append({"kind": "auth", "status": "failed", "error": str(exc), "current_url": page.url})


def click_nav_and_capture(
    page: Page,
    base_url: str,
    step: Dict[str, str],
    debug_dir: Path,
    stamp: str,
    viewport_name: str,
) -> Dict[str, Any]:
    selector = step["selector"]
    expected_path = step["expected_path"]
    step_name = f"nav_{step['name']}"
    nav_finding: Optional[Dict[str, Any]] = None
    try:
        link = page.locator(selector).first
        link.wait_for(state="visible", timeout=8_000)
        href = link.get_attribute("href")
        link.click(timeout=8_000)
        expected_url = same_origin_url(base_url, expected_path)
        try:
            page.wait_for_url(lambda url: urlparse(url).path == expected_path, timeout=12_000)
        except PlaywrightTimeoutError:
            nav_finding = {
                "severity": "high",
                "step": f"{viewport_name}:{step_name}",
                "kind": "navigation",
                "message": f"Click did not navigate to {expected_path}.",
                "href": href,
                "expected_url": expected_url,
                "actual_url": page.url,
            }
    except PlaywrightError as exc:
        nav_finding = {
            "severity": "high",
            "step": f"{viewport_name}:{step_name}",
            "kind": "navigation",
            "message": f"Could not click navbar target {selector}.",
            "error": str(exc),
            "actual_url": page.url,
        }
    captured = capture_step(page, debug_dir, stamp, viewport_name, step_name)
    if nav_finding:
        captured["findings"].insert(0, nav_finding)
    return captured


def audit_viewport(
    context: Any,
    base_url: str,
    debug_dir: Path,
    stamp: str,
    viewport_name: str,
    args: argparse.Namespace,
    events: List[Dict[str, Any]],
    notes: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    page = context.new_page()
    bind_observers(page, events)
    page.set_default_timeout(args.timeout)
    steps: List[Dict[str, Any]] = []
    page.goto(same_origin_url(base_url, "/"), wait_until="domcontentloaded", timeout=args.timeout)
    steps.append(capture_step(page, debug_dir, stamp, viewport_name, "initial_home"))
    if viewport_name == "desktop":
        attempt_login(page, args, notes)
        steps.append(capture_step(page, debug_dir, stamp, viewport_name, "post_auth_check"))
    for step in NAV_STEPS:
        steps.append(click_nav_and_capture(page, base_url, step, debug_dir, stamp, viewport_name))
    page.close()
    return steps


def summarize_findings(steps: List[Dict[str, Any]], events: List[Dict[str, Any]], notes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    for step in steps:
        findings.extend(step.get("findings", []))
    for event in events:
        if event.get("severity"):
            findings.append(
                {
                    "severity": event["severity"],
                    "step": "browser-runtime",
                    "kind": event.get("event_type"),
                    "message": event.get("text") or event.get("url") or "Browser runtime event",
                    "event": event,
                }
            )
    for note in notes:
        if note.get("status") in {"failed"}:
            findings.append(
                {
                    "severity": "medium",
                    "step": "auth",
                    "kind": "auth",
                    "message": note.get("error") or note.get("reason") or "Authentication issue",
                    "note": note,
                }
            )
    return findings


def write_markdown_report(report_path: Path, report: Dict[str, Any]) -> None:
    lines = [
        "# Ambitionz Rebirth UI Audit",
        "",
        f"- Base URL: {report['base_url']}",
        f"- Timestamp: {report['timestamp']}",
        f"- Browser path: {report['browser_path']}",
        f"- Total findings: {len(report['findings'])}",
        "",
        "## Findings",
    ]
    if report["findings"]:
        for finding in report["findings"]:
            lines.append(
                f"- [{finding.get('severity', 'info')}] {finding.get('step')} / {finding.get('kind')}: {finding.get('message')}"
            )
    else:
        lines.append("- No high/medium UI, route, network or console findings detected.")
    lines.extend(["", "## Screenshots"])
    for step in report["steps"]:
        lines.append(f"- {step['name']} ({step['path']}): `{step['screenshot']}`")
    lines.extend(["", "## Auth Notes"])
    for note in report["notes"]:
        lines.append(f"- {note.get('status')}: {note.get('reason') or note.get('error') or note.get('current_url')}")
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit Rebirth UI routes, console logs, screenshots and card rendering.")
    parser.add_argument("--base-url", default=os.environ.get("UI_AUDITOR_URL", DEFAULT_BASE_URL))
    parser.add_argument("--debug-dir", default=str(DEFAULT_DEBUG_DIR))
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_MS)
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--skip-login", action="store_true")
    parser.add_argument("--login-email", default=os.environ.get("UI_AUDITOR_EMAIL"))
    parser.add_argument("--login-password", default=os.environ.get("UI_AUDITOR_PASSWORD"))
    parser.add_argument("--viewport", choices=["desktop", "mobile390", "all"], default="all")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base_url = normalize_base_url(args.base_url)
    debug_dir = Path(args.debug_dir)
    ensure_dir(debug_dir)
    stamp = utc_stamp()
    events: List[Dict[str, Any]] = []
    notes: List[Dict[str, Any]] = []
    steps: List[Dict[str, Any]] = []
    selected_viewports = list(VIEWPORTS.keys()) if args.viewport == "all" else [args.viewport]

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not args.headed)
        for viewport_name in selected_viewports:
            viewport = VIEWPORTS[viewport_name]
            context = browser.new_context(
                viewport={"width": viewport["width"], "height": viewport["height"]},
                is_mobile=viewport["is_mobile"],
                device_scale_factor=2 if viewport["is_mobile"] else 1,
                ignore_https_errors=True,
                record_har_path=str(debug_dir / f"{stamp}_{viewport_name}.har"),
            )
            steps.extend(audit_viewport(context, base_url, debug_dir, stamp, viewport_name, args, events, notes))
            context.close()
        browser.close()

    findings = summarize_findings(steps, events, notes)
    report = {
        "base_url": base_url,
        "timestamp": stamp,
        "browser_path": "Playwright Python (user explicitly requested automation script)",
        "debug_dir": str(debug_dir),
        "notes": notes,
        "steps": steps,
        "events": events,
        "findings": findings,
    }
    report_json = debug_dir / f"{stamp}_ui_audit_report.json"
    report_md = debug_dir / f"{stamp}_ui_audit_report.md"
    console_jsonl = debug_dir / f"{stamp}_browser_events.jsonl"
    write_json(report_json, report)
    append_jsonl(console_jsonl, events)
    write_markdown_report(report_md, report)
    print(json.dumps({"report": str(report_json), "markdown": str(report_md), "events": str(console_jsonl), "findings": len(findings)}, indent=2))
    return 1 if any(f.get("severity") == "high" for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
