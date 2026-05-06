from pathlib import Path
import re
import sys

ROOT = Path(".").resolve()
sys.path.insert(0, str(ROOT))

SCAN_DIRS = ["."]
IGNORE_DIRS = {
    ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    "node_modules", "android", "ios", "dist", "build",
    "backups", "reports", "tests", "migrations", "tools",
}

ALLOW_FILES = {
    "app.py",
    "config.py",
    "models.py",
}

ALLOW_DIR_PREFIXES = {
    "routes",
    "services",
    "sockets",
    "game",
}

def is_active_file(path: Path) -> bool:
    if any(part in IGNORE_DIRS for part in path.parts):
        return False

    rel = path.relative_to(ROOT)
    first = rel.parts[0]

    if path.name in ALLOW_FILES:
        return True

    if first in ALLOW_DIR_PREFIXES:
        return True

    return False

PY_FILES = [
    p for p in ROOT.rglob("*.py")
    if p.is_file() and is_active_file(p)
]

def rel(p):
    return str(p.relative_to(ROOT))

def read(p):
    return p.read_text(encoding="utf-8", errors="ignore")

print("=" * 80)
print("SECURITY ROUTE AUDIT CLEAN - ACTIVE APP CODE ONLY")
print("=" * 80)

print("\n[1] Active Python files scanned:")
for p in PY_FILES:
    print("-", rel(p))

print("\n[2] Admin/debug/danger routes with nearby protection:")
route_re = re.compile(r"@app\.route\(['\"]([^'\"]+)['\"](?:,\s*methods=\[([^\]]+)\])?")
danger_words = ("admin", "debug", "reset", "delete", "clear", "promote", "toggle", "dev-tools", "test-email")

for path in PY_FILES:
    text = read(path)
    lines = text.splitlines()

    for m in route_re.finditer(text):
        route = m.group(1)
        methods = m.group(2) or "GET"

        if any(w in route.lower() for w in danger_words):
            line_no = text[:m.start()].count("\n") + 1
            start = max(1, line_no)
            end = min(len(lines), line_no + 20)
            block = "\n".join(lines[start-1:end])

            has_admin_guard = "admin_required_redirect()" in block
            has_dev_guard = "dev_tools_required_redirect()" in block
            has_danger_confirmation = "require_danger_confirmation_or_redirect()" in block

            status = []
            if has_admin_guard:
                status.append("ADMIN_GUARD")
            if has_dev_guard:
                status.append("DEV_GUARD")
            if has_danger_confirmation:
                status.append("DANGER_CONFIRM")

            if not status:
                status.append("NO_LOCAL_GUARD_FOUND")

            print(f"{rel(path)}:{line_no} {route} methods={methods} -> {', '.join(status)}")

print("\n[3] Hardcoded dangerous secrets in active app code:")
secret_patterns = [
    ("SECRET_KEY hardcoded", r"SECRET_KEY\s*=\s*['\"][^'\"]{8,}['\"]"),
    ("Password variable hardcoded", r"\bPASSWORD\s*=\s*['\"][^'\"]{4,}['\"]"),
    ("Token/API key hardcoded", r"\b(token|api_key|apikey|private_key)\s*=\s*['\"][^'\"]{8,}['\"]"),
    ("Database URL literal", r"postgres(?:ql)?://[^'\"\s]+"),
]

found = False
for path in PY_FILES:
    text = read(path)
    for label, pattern in secret_patterns:
        for m in re.finditer(pattern, text, flags=re.I):
            found = True
            line = text[:m.start()].count("\n") + 1
            print(f"[SECRET] {label}: {rel(path)}:{line} -> {m.group(0)[:140]}")

if not found:
    print("OK - nenhum segredo óbvio em código ativo.")

print("\n[4] Dangerous functions in active app code:")
danger_patterns = [
    ("eval", r"\beval\s*\("),
    ("exec", r"\bexec\s*\("),
    ("shell=True", r"shell\s*=\s*True"),
]

found = False
for path in PY_FILES:
    text = read(path)
    for label, pattern in danger_patterns:
        for m in re.finditer(pattern, text):
            found = True
            line = text[:m.start()].count("\n") + 1
            print(f"[DANGER] {label}: {rel(path)}:{line}")

if not found:
    print("OK - eval/exec/shell=True não encontrados em código ativo.")

print("\n[5] Flask import and route count:")
try:
    from app import app
    print("APP IMPORT OK")
    print("Total routes:", len(app.url_map._rules))

    duplicate_rules = {}
    for rule in app.url_map.iter_rules():
        duplicate_rules.setdefault(str(rule), []).append(rule.endpoint)

    duplicates = {
        route: endpoints
        for route, endpoints in duplicate_rules.items()
        if len(endpoints) > 1
    }

    if duplicates:
        print("\nDuplicate URL rules detected:")
        for route, endpoints in duplicates.items():
            print(f"- {route}: {endpoints}")
    else:
        print("OK - nenhuma URL duplicada detectada.")

except Exception as e:
    print("APP IMPORT FAILED")
    print(type(e).__name__, str(e))

print("\nAUDIT DONE")
