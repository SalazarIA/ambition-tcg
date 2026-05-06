from pathlib import Path
from datetime import datetime
import subprocess
import sys
import re
import json
import os

ROOT = Path(".").resolve()
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUT = ROOT / "reports" / f"full_game_audit_{STAMP}.md"

IGNORE_DIRS = {
    ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    "node_modules", "android", "ios", "dist", "build",
    "backups", "reports", "migrations",
}

ACTIVE_DIRS = {"routes", "services", "sockets", "game", "static", "templates"}
ACTIVE_ROOT_FILES = {
    "app.py", "config.py", "models.py", "render.yaml",
    "requirements.txt", "package.json",
}

def is_ignored(path: Path) -> bool:
    return any(part in IGNORE_DIRS for part in path.parts)

def active_file(path: Path) -> bool:
    if not path.is_file() or is_ignored(path):
        return False

    rel = path.relative_to(ROOT)
    first = rel.parts[0]

    if path.name in ACTIVE_ROOT_FILES:
        return True

    if first in ACTIVE_DIRS:
        return True

    return False

def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")

def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))

def sh(cmd, timeout=80):
    try:
        p = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except FileNotFoundError:
        return 127, "", "command not found"
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"

def add(lines, text=""):
    lines.append(text)

def section(lines, title):
    add(lines, "")
    add(lines, f"## {title}")
    add(lines, "")

def code(lines, text, lang="text"):
    add(lines, f"```{lang}")
    add(lines, text.strip() if text else "")
    add(lines, "```")

def command_report(lines, title, cmd, timeout=80):
    section(lines, title)
    add(lines, f"Command: `{' '.join(cmd)}`")
    rc, out, err = sh(cmd, timeout=timeout)
    add(lines, f"Exit code: `{rc}`")
    if out:
        add(lines, "")
        add(lines, "STDOUT:")
        code(lines, out)
    if err:
        add(lines, "")
        add(lines, "STDERR:")
        code(lines, err)
    return rc, out, err

def find_pattern(files, patterns):
    hits = []
    for path in files:
        text = read(path)
        for label, pattern, flags in patterns:
            for m in re.finditer(pattern, text, flags):
                line = text[:m.start()].count("\n") + 1
                preview = m.group(0).replace("\n", " ")[:220]
                hits.append((label, rel(path), line, preview))
    return hits

def main():
    lines = []

    files = [p for p in ROOT.rglob("*") if active_file(p)]
    py_files = [p for p in files if p.suffix == ".py"]
    js_files = [p for p in files if p.suffix == ".js"]
    html_files = [p for p in files if p.suffix == ".html"]
    css_files = [p for p in files if p.suffix == ".css"]

    add(lines, "# Ambitionz — Full Game Audit")
    add(lines, "")
    add(lines, f"Generated: `{datetime.now().isoformat(timespec='seconds')}`")
    add(lines, f"Root: `{ROOT}`")
    add(lines, "")
    add(lines, f"Active files scanned: `{len(files)}`")
    add(lines, f"Python: `{len(py_files)}` | JS: `{len(js_files)}` | HTML: `{len(html_files)}` | CSS: `{len(css_files)}`")

    command_report(lines, "Git status", ["git", "status", "--short"])
    command_report(lines, "Git latest commits", ["git", "log", "--oneline", "-8"])
    command_report(lines, "Git diff stat", ["git", "diff", "--stat"])
    command_report(lines, "Git diff check", ["git", "diff", "--check"])

    if py_files:
        command_report(lines, "Python compile active files", [sys.executable, "-m", "py_compile", *map(str, py_files)], timeout=120)

    for js in js_files:
        if "service-worker" in js.name or "pwa" in js.name or "game" in js.name or "deck" in js.name or "battle" in js.name:
            command_report(lines, f"Node syntax check — {rel(js)}", ["node", "--check", str(js)])

    command_report(lines, "Pytest quick suite", ["pytest", "-q"], timeout=180)
    command_report(lines, "Preflight", [sys.executable, "tools/preflight.py"], timeout=120)
    command_report(lines, "Internal RC check", [sys.executable, "tools/internal_rc_check.py"], timeout=120)

    if (ROOT / "tools" / "arena_playtest.py").exists():
        command_report(lines, "Arena automated playtest", [sys.executable, "tools/arena_playtest.py"], timeout=180)

    command_report(lines, "pip-audit", ["pip-audit", "-r", "requirements.txt"], timeout=120)
    command_report(lines, "bandit active app", ["bandit", "-q", "-r", "app.py", "routes", "services", "sockets", "game"], timeout=120)

    if (ROOT / "package.json").exists():
        command_report(lines, "npm audit production", ["npm", "audit", "--omit=dev"], timeout=120)

    section(lines, "Security pattern scan")

    security_patterns = [
        ("Hardcoded SECRET_KEY", r"SECRET_KEY\s*=\s*['\"][^'\"]{8,}['\"]", re.I),
        ("Hardcoded password variable", r"\b(PASSWORD|password)\s*=\s*['\"][^'\"]{4,}['\"]", re.I),
        ("Hardcoded token/api key", r"\b(token|api_key|apikey|private_key)\s*=\s*['\"][^'\"]{8,}['\"]", re.I),
        ("Database URL literal", r"postgres(?:ql)?://[^'\"\s]+", re.I),
        ("debug=True", r"debug\s*=\s*True", re.I),
        ("eval usage", r"\beval\s*\(", 0),
        ("exec usage", r"\bexec\s*\(", 0),
        ("shell=True", r"shell\s*=\s*True", 0),
        ("raw SQL execute likely", r"\.execute\s*\(\s*f?['\"]", re.I),
        ("CSRF disabled suspicious", r"csrf.*(False|disable|disabled)", re.I),
    ]

    hits = find_pattern([p for p in files if p.suffix in {".py", ".yaml", ".yml", ".env", ".txt"} or p.name in {"render.yaml"}], security_patterns)
    if hits:
        for label, file, line, preview in hits:
            add(lines, f"- **{label}** — `{file}:{line}` → `{preview}`")
    else:
        add(lines, "OK — no obvious critical security patterns found in active code.")

    section(lines, "Admin/danger route protection scan")
    route_re = re.compile(r"@app\.route\(['\"]([^'\"]+)['\"](?:,\s*methods=\[([^\]]+)\])?")
    danger_words = ("admin", "debug", "reset", "delete", "clear", "promote", "toggle", "dev-tools", "test-email", "beta-event")

    for path in py_files:
        text = read(path)
        lines_split = text.splitlines()
        for m in route_re.finditer(text):
            route = m.group(1)
            methods = m.group(2) or "GET"
            if not any(w in route.lower() for w in danger_words):
                continue

            line_no = text[:m.start()].count("\n") + 1
            start = max(1, line_no)
            end = min(len(lines_split), line_no + 26)
            block = "\n".join(lines_split[start-1:end])

            guards = []
            if "admin_required_redirect()" in block:
                guards.append("ADMIN_GUARD")
            if "dev_tools_required_redirect()" in block:
                guards.append("DEV_GUARD")
            if "require_danger_confirmation_or_redirect()" in block:
                guards.append("DANGER_CONFIRM")
            if "rate_limit" in block.lower() or "limiter" in block.lower():
                guards.append("RATE_LIMIT")
            if "allowed" in block.lower() and "event" in route.lower():
                guards.append("ALLOWLIST_HINT")

            if not guards:
                guards.append("NO_LOCAL_GUARD_FOUND")

            add(lines, f"- `{rel(path)}:{line_no}` `{route}` methods=`{methods}` → **{', '.join(guards)}**")

    section(lines, "Duplicate route scan")
    try:
        sys.path.insert(0, str(ROOT))
        from app import app

        route_map = {}
        for rule in app.url_map.iter_rules():
            route_map.setdefault(str(rule), []).append(rule.endpoint)

        dupes = {k: v for k, v in route_map.items() if len(v) > 1}

        add(lines, f"Total Flask routes: `{len(app.url_map._rules)}`")

        if dupes:
            add(lines, "")
            add(lines, "Duplicate URL rules:")
            for route, endpoints in dupes.items():
                add(lines, f"- `{route}` → `{endpoints}`")
        else:
            add(lines, "OK — no duplicate URL rules detected.")
    except Exception as e:
        add(lines, f"APP IMPORT FAILED: `{type(e).__name__}: {e}`")

    section(lines, "Socket.IO compatibility scan")

    backend_on = set()
    backend_emit = set()
    frontend_on = set()
    frontend_emit = set()

    for path in py_files:
        text = read(path)
        backend_on.update(re.findall(r"@socketio\.on\(['\"]([^'\"]+)['\"]\)", text))
        backend_emit.update(re.findall(r"socketio\.emit\(['\"]([^'\"]+)['\"]", text))

    for path in js_files + html_files:
        text = read(path)
        frontend_on.update(re.findall(r"socket\.on\(['\"]([^'\"]+)['\"]", text))
        frontend_emit.update(re.findall(r"socket\.emit\(['\"]([^'\"]+)['\"]", text))

    ignored_socket = {"connect", "disconnect", "connect_error"}

    missing_backend = sorted(frontend_emit - backend_on - ignored_socket)
    missing_frontend = sorted(backend_emit - frontend_on - ignored_socket)

    add(lines, f"Backend listeners: `{len(backend_on)}`")
    add(lines, f"Backend emits: `{len(backend_emit)}`")
    add(lines, f"Frontend listeners: `{len(frontend_on)}`")
    add(lines, f"Frontend emits: `{len(frontend_emit)}`")

    if missing_backend:
        add(lines, "")
        add(lines, "Frontend emits without backend listener:")
        for item in missing_backend:
            add(lines, f"- `{item}`")
    else:
        add(lines, "")
        add(lines, "OK — every frontend emit has backend listener.")

    if missing_frontend:
        add(lines, "")
        add(lines, "Backend emits without frontend listener:")
        for item in missing_frontend:
            add(lines, f"- `{item}`")
    else:
        add(lines, "")
        add(lines, "OK — every backend emit has frontend listener.")

    section(lines, "Template and static asset scan")

    template_refs = []
    missing_templates = []
    render_re = re.compile(r"render_template\(['\"]([^'\"]+)['\"]")

    for path in py_files:
        text = read(path)
        for m in render_re.finditer(text):
            tpl = m.group(1)
            template_refs.append(tpl)
            if not (ROOT / "templates" / tpl).exists():
                line = text[:m.start()].count("\n") + 1
                missing_templates.append((rel(path), line, tpl))

    if missing_templates:
        add(lines, "Missing templates:")
        for file, line, tpl in missing_templates:
            add(lines, f"- `{file}:{line}` → `templates/{tpl}`")
    else:
        add(lines, "OK — no missing templates referenced by Flask.")

    asset_re = re.compile(r"""(?:url_for\(['"]static['"],\s*filename=['"]([^'"]+)['"]\)|['"]/(static/[^'"]+)['"])""")
    missing_assets = []

    for path in html_files:
        text = read(path)
        for m in asset_re.finditer(text):
            asset = m.group(1) or m.group(2)
            asset_path = ROOT / asset if asset.startswith("static/") else ROOT / "static" / asset
            if not asset_path.exists():
                line = text[:m.start()].count("\n") + 1
                missing_assets.append((rel(path), line, str(asset_path.relative_to(ROOT))))

    if missing_assets:
        add(lines, "")
        add(lines, "Missing static assets:")
        for file, line, asset in missing_assets:
            add(lines, f"- `{file}:{line}` → `{asset}`")
    else:
        add(lines, "OK — no missing static assets referenced by templates.")

    section(lines, "PWA scan")

    manifest = ROOT / "static" / "manifest.webmanifest"
    sw_static = ROOT / "static" / "js" / "service-worker.js"

    if manifest.exists():
        try:
            data = json.loads(read(manifest))
            required = ["name", "short_name", "start_url", "display", "icons"]
            for key in required:
                add(lines, f"- manifest `{key}`: {'OK' if key in data else 'MISSING'}")
            icons = data.get("icons", [])
            add(lines, f"- manifest icons: `{len(icons)}`")
            for icon in icons:
                src = icon.get("src", "")
                if src:
                    icon_path = ROOT / src.lstrip("/")
                    add(lines, f"  - `{src}` exists: `{icon_path.exists()}`")
        except Exception as e:
            add(lines, f"Manifest parse failed: `{type(e).__name__}: {e}`")
    else:
        add(lines, "MISSING — `static/manifest.webmanifest`")

    if sw_static.exists():
        sw_text = read(sw_static)
        add(lines, f"- service-worker file exists: OK")
        add(lines, f"- contains install listener: `{'install' in sw_text}`")
        add(lines, f"- contains fetch listener: `{'fetch' in sw_text}`")
        add(lines, f"- contains cache usage: `{'caches' in sw_text}`")
    else:
        add(lines, "MISSING — `static/js/service-worker.js`")

    section(lines, "UX/polish heuristic scan")

    polish_patterns = [
        ("TODO", r"\bTODO\b", re.I),
        ("FIXME", r"\bFIXME\b", re.I),
        ("console.log", r"\bconsole\.log\s*\(", 0),
        ("alert()", r"\balert\s*\(", 0),
        ("inline onclick", r"onclick\s*=", re.I),
        ("hardcoded localhost", r"localhost|127\.0\.0\.1", re.I),
        ("temporary copy", r"\b(temp|temporary|placeholder|lorem ipsum)\b", re.I),
    ]

    polish_hits = find_pattern([p for p in files if p.suffix in {".py", ".js", ".html", ".css"}], polish_patterns)

    if polish_hits:
        for label, file, line, preview in polish_hits[:250]:
            add(lines, f"- **{label}** — `{file}:{line}` → `{preview}`")
        if len(polish_hits) > 250:
            add(lines, f"- Output truncated. Total polish hits: `{len(polish_hits)}`")
    else:
        add(lines, "OK — no obvious temporary/debug polish issues found.")

    section(lines, "Large active files")
    sizes = sorted([(p.stat().st_size, p) for p in files], reverse=True)
    for size, path in sizes[:20]:
        add(lines, f"- `{rel(path)}` — `{size}` bytes")

    section(lines, "Immediate review checklist")
    add(lines, "- Check every `NO_LOCAL_GUARD_FOUND` route manually.")
    add(lines, "- Confirm `/service-worker.js` is served from root scope `/`, not only `/static/js/`.")
    add(lines, "- Confirm destructive admin POSTs require CSRF + admin + danger confirmation.")
    add(lines, "- Confirm forgot-password response never reveals whether an email exists.")
    add(lines, "- Confirm beta event route allowlists event names and rate limits IP/session.")
    add(lines, "- Confirm Render deploy ran migrations before app start.")
    add(lines, "- Confirm mobile install works on Android Chrome and iOS Safari.")
    add(lines, "- Confirm Arena reconnect, refresh, disconnect and surrender flows.")
    add(lines, "- Confirm bot fallback cannot create duplicate active matches.")
    add(lines, "- Confirm no generated reports/snapshots should be committed unless intentional.")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"FULL AUDIT CREATED: {OUT}")

if __name__ == "__main__":
    main()
