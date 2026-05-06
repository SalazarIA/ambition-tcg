from pathlib import Path
import re

ROOT = Path(".").resolve()

IGNORE_DIRS = {
    ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    "node_modules", "android", "ios", "dist", "build",
    "backups", "reports", "tests", "migrations",
}

PY_FILES = [
    p for p in ROOT.rglob("*.py")
    if not any(part in IGNORE_DIRS for part in p.parts)
]

def rel(p):
    return str(p.relative_to(ROOT))

def read(p):
    return p.read_text(encoding="utf-8", errors="ignore")

print("=" * 80)
print("SECURITY ROUTE AUDIT - ACTIVE CODE ONLY")
print("=" * 80)

print("\n[1] Active Python files scanned:")
for p in PY_FILES:
    print("-", rel(p))

print("\n[2] Admin/debug/danger routes with nearby code:")
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
            start = max(1, line_no - 6)
            end = min(len(lines), line_no + 18)

            print("\n" + "-" * 80)
            print(f"{rel(path)}:{line_no} route={route} methods={methods}")
            print("-" * 80)
            for i in range(start, end + 1):
                marker = ">>" if i == line_no else "  "
                print(f"{marker} {i:04d}: {lines[i-1]}")

print("\n[3] Hardcoded dangerous secrets in active code:")
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

print("\n[4] Dangerous functions in active code:")
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

print("\n[5] Flask import:")
try:
    from app import app
    print("APP IMPORT OK")
    print("Total routes:", len(app.url_map._rules))
except Exception as e:
    print("APP IMPORT FAILED")
    print(type(e).__name__, str(e))

print("\nAUDIT DONE")
