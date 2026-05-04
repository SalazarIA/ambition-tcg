from pathlib import Path
import ast
import re
import subprocess
import sys

ROOT = Path(".")
REPORT = Path("reports/deep_audit_report.md")

FILES = list(ROOT.rglob("*"))

IGNORE_DIRS = {
    ".git", ".venv", "venv", "__pycache__", "node_modules",
    ".mypy_cache", ".pytest_cache", "dist", "build"
}

def skip(path):
    return any(part in IGNORE_DIRS for part in path.parts)

def run_cmd(cmd):
    try:
        result = subprocess.run(
            cmd,
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=60
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return 999, "", str(e)

def section(title):
    lines.append(f"\n## {title}\n")

def add(text=""):
    lines.append(str(text))

lines = []
add("# Ambitionz Deep Audit Report")

# 1. Git
section("Git status")
code, out, err = run_cmd(["git", "status", "--short"])
add("```")
add(out or "(clean)")
add(err)
add("```")

# 2. Python compile
section("Python compileall")
code, out, err = run_cmd([sys.executable, "-m", "compileall", "app.py", "game", "services", "tools"])
add(f"Exit code: {code}")
add("```")
add(out)
add(err)
add("```")

# 3. JS syntax
section("JavaScript syntax check")
js_files = [p for p in ROOT.rglob("static/js/*.js") if not skip(p)]
if not js_files:
    add("No JS files found.")
else:
    for js in js_files:
        code, out, err = run_cmd(["node", "--check", str(js)])
        status = "OK" if code == 0 else "FAIL"
        add(f"- `{js}`: {status}")
        if out or err:
            add("```")
            add(out)
            add(err)
            add("```")

# 4. Routes inventory
section("Flask routes")
app_py = Path("app.py")
if app_py.exists():
    text = app_py.read_text(errors="ignore")
    routes = re.findall(r'@app\.route\((.*?)\)\s*\ndef\s+([a-zA-Z0-9_]+)', text, re.S)
    for raw, fn in routes:
        add(f"- `{fn}`: `{raw.strip()}`")
else:
    add("app.py not found.")

# 5. Socket handlers
section("Socket.IO handlers")
if app_py.exists():
    handlers = re.findall(r'@socketio\.on\(["\'](.+?)["\']\)\s*\ndef\s+([a-zA-Z0-9_]+)', text, re.S)
    seen = {}
    for event, fn in handlers:
        seen.setdefault(event, []).append(fn)
        add(f"- `{event}` -> `{fn}`")

    duplicates = {k: v for k, v in seen.items() if len(v) > 1}
    if duplicates:
        add("\n### Duplicate socket handlers found")
        for event, funcs in duplicates.items():
            add(f"- `{event}`: {funcs}")
    else:
        add("\nNo duplicate socket handlers found.")

# 6. Suspicious auth/login checks
section("Auth/login scan")
if app_py.exists():
    patterns = [
        "check_password", "password_hash", "account_status",
        "is_verified", "login_attempts", "request.form"
    ]
    for i, line in enumerate(text.splitlines(), 1):
        if any(p in line for p in patterns):
            add(f"{i}: `{line.strip()}`")

# 7. Model fields
section("Model scan")
models = Path("models.py")
if models.exists():
    mtext = models.read_text(errors="ignore")
    for i, line in enumerate(mtext.splitlines(), 1):
        if any(k in line for k in ["class User", "password_hash", "set_password", "check_password", "account_status", "is_admin", "is_verified"]):
            add(f"{i}: `{line.strip()}`")
else:
    add("models.py not found.")

# 8. Broken references: function calls not defined in same file rough scan
section("Rough undefined function scan in app.py")
if app_py.exists():
    try:
        tree = ast.parse(text)
        defs = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
        calls = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Call):
                if isinstance(n.func, ast.Name):
                    calls.add(n.func.id)
        builtin_allow = set(dir(__builtins__)) | {
            "print", "len", "int", "str", "bool", "float", "dict", "list", "set",
            "jsonify", "render_template", "redirect", "url_for", "flash",
            "request", "session", "datetime", "timezone"
        }
        suspicious = sorted(c for c in calls if c not in defs and c not in builtin_allow and not c[0].isupper())
        for c in suspicious[:200]:
            add(f"- `{c}`")
    except Exception as e:
        add(f"AST scan failed: {e}")

# 9. TODO/FIXME/errors
section("TODO/FIXME/Error strings")
for p in FILES:
    if skip(p) or not p.is_file():
        continue
    if p.suffix.lower() not in [".py", ".js", ".html", ".css", ".md", ".yaml", ".yml"]:
        continue
    try:
        content = p.read_text(errors="ignore")
    except Exception:
        continue
    for i, line in enumerate(content.splitlines(), 1):
        low = line.lower()
        if any(k in low for k in ["todo", "fixme", "hack", "broken", "error:", "except exception", "pass  #"]):
            add(f"- `{p}:{i}` {line.strip()[:180]}")

# 10. Security quick scan
section("Security quick scan")
security_patterns = [
    ("Hardcoded password", r'password\s*=\s*["\'][^"\']+["\']'),
    ("Secret key", r'SECRET_KEY\s*='),
    ("Debug true", r'debug\s*=\s*True'),
    ("CORS wildcard", r'cors_allowed_origins\s*=\s*["\']\*["\']'),
    ("Email body logging", r'EMAIL_LOG_BODY_ENABLED.*true'),
]
for p in FILES:
    if skip(p) or not p.is_file():
        continue
    if p.suffix.lower() not in [".py", ".js", ".yaml", ".yml", ".env", ".txt"]:
        continue
    try:
        content = p.read_text(errors="ignore")
    except Exception:
        continue
    for label, pat in security_patterns:
        for m in re.finditer(pat, content, re.I):
            line_no = content[:m.start()].count("\n") + 1
            add(f"- {label}: `{p}:{line_no}`")

# 11. Existing project checks
section("Existing project checks")
for cmd in [
    [sys.executable, "tools/preflight.py"],
    [sys.executable, "tools/internal_rc_check.py"],
]:
    if Path(cmd[1]).exists():
        code, out, err = run_cmd(cmd)
        add(f"### {' '.join(cmd)}")
        add(f"Exit code: {code}")
        add("```")
        add(out)
        add(err)
        add("```")

REPORT.write_text("\n".join(lines))
print(f"Deep audit finished: {REPORT}")
