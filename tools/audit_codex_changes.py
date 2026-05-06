from pathlib import Path
import re
import ast
import subprocess
import sys

ROOT = Path(".").resolve()

IGNORE_DIRS = {
    ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    "node_modules", "android", "ios", "dist", "build", ".next",
}

TEXT_EXTS = {
    ".py", ".html", ".css", ".js", ".json", ".md", ".txt", ".yml", ".yaml",
    ".env", ".example",
}

SECRET_PATTERNS = [
    ("SECRET_KEY hardcoded", r"SECRET_KEY\s*=\s*['\"][^'\"]{8,}['\"]"),
    ("Password hardcoded", r"password\s*=\s*['\"][^'\"]{4,}['\"]"),
    ("Token hardcoded", r"(token|api_key|apikey|private_key)\s*=\s*['\"][^'\"]{8,}['\"]"),
    ("Potential Render/DB URL", r"postgres(ql)?://[^'\"\s]+"),
    ("Potential SMTP password", r"MAIL_PASSWORD\s*=\s*['\"][^'\"]+['\"]"),
]

RISK_PATTERNS = [
    ("Debug mode enabled", r"debug\s*=\s*True"),
    ("Flask app.run debug", r"app\.run\(.*debug\s*=\s*True"),
    ("Dangerous eval", r"\beval\s*\("),
    ("Dangerous exec", r"\bexec\s*\("),
    ("Shell=True usage", r"shell\s*=\s*True"),
    ("Direct SQL execute", r"\.execute\s*\(\s*f?['\"]"),
    ("CSRF disabled/suspicious", r"csrf.*(False|disable|disabled)"),
    ("Admin route", r"@app\.route\(['\"][^'\"]*admin"),
    ("Dangerous route", r"dangerous|reset|delete|wipe|promote|dev-tools"),
]

SOCKET_BACKEND_ON = re.compile(r"@socketio\.on\(['\"]([^'\"]+)['\"]\)")
SOCKET_BACKEND_EMIT = re.compile(r"socketio\.emit\(['\"]([^'\"]+)['\"]")
SOCKET_FRONTEND_ON = re.compile(r"socket\.on\(['\"]([^'\"]+)['\"]")
SOCKET_FRONTEND_EMIT = re.compile(r"socket\.emit\(['\"]([^'\"]+)['\"]")

def should_skip(path: Path) -> bool:
    return any(part in IGNORE_DIRS for part in path.parts)

def iter_files():
    for path in ROOT.rglob("*"):
        if path.is_file() and not should_skip(path):
            if path.suffix in TEXT_EXTS or path.name.startswith(".env"):
                yield path

def read(path: Path):
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return ""

def rel(path: Path):
    return str(path.relative_to(ROOT))

def run_cmd(cmd):
    print(f"\n$ {' '.join(cmd)}")
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
        if p.stdout.strip():
            print(p.stdout)
        if p.stderr.strip():
            print(p.stderr)
        print(f"exit={p.returncode}")
        return p.returncode
    except FileNotFoundError:
        print("comando não encontrado")
        return 127
    except subprocess.TimeoutExpired:
        print("timeout")
        return 124

print("=" * 80)
print("AUDIT CODEX CHANGES - AMBITIONZ")
print("=" * 80)

print("\n[1] GIT STATUS")
run_cmd(["git", "status", "--short"])

print("\n[2] ÚLTIMOS ARQUIVOS ALTERADOS")
run_cmd(["git", "diff", "--name-only"])
run_cmd(["git", "diff", "--stat"])

print("\n[3] PYTHON SYNTAX CHECK")
py_files = [str(p) for p in iter_files() if p.suffix == ".py"]
if py_files:
    run_cmd([sys.executable, "-m", "py_compile", *py_files])
else:
    print("Nenhum arquivo .py encontrado.")

print("\n[4] JS SYNTAX CHECK")
js_files = [str(p) for p in iter_files() if p.suffix == ".js" and "static" in p.parts]
if js_files:
    for js in js_files:
        run_cmd(["node", "--check", js])
else:
    print("Nenhum JS em static encontrado.")

print("\n[5] PROCURA POR SEGREDOS E CONFIGS PERIGOSAS")
findings = []
for path in iter_files():
    text = read(path)
    for label, pattern in SECRET_PATTERNS:
        for m in re.finditer(pattern, text, flags=re.I):
            line = text[:m.start()].count("\n") + 1
            findings.append(("SECRET", label, rel(path), line, m.group(0)[:120]))
    for label, pattern in RISK_PATTERNS:
        for m in re.finditer(pattern, text, flags=re.I | re.S):
            line = text[:m.start()].count("\n") + 1
            findings.append(("RISK", label, rel(path), line, m.group(0)[:120].replace("\n", " ")))

if findings:
    for kind, label, file, line, preview in findings:
        print(f"[{kind}] {label}: {file}:{line} -> {preview}")
else:
    print("OK - nenhum padrão crítico encontrado.")

print("\n[6] ROTAS FLASK ENCONTRADAS")
route_re = re.compile(r"@app\.route\(['\"]([^'\"]+)['\"](?:,\s*methods=\[([^\]]+)\])?")
for path in iter_files():
    if path.suffix == ".py":
        text = read(path)
        for m in route_re.finditer(text):
            line = text[:m.start()].count("\n") + 1
            route = m.group(1)
            methods = m.group(2) or "GET default"
            marker = ""
            if any(x in route.lower() for x in ["admin", "dev", "reset", "delete", "promote", "dangerous", "test"]):
                marker = "  <-- REVISAR"
            print(f"{rel(path)}:{line} {route} methods={methods}{marker}")

print("\n[7] SOCKET.IO - FRONT/BACK COMPATIBILIDADE")
backend_on = set()
backend_emit = set()
frontend_on = set()
frontend_emit = set()

for path in iter_files():
    text = read(path)
    if path.suffix == ".py":
        backend_on.update(SOCKET_BACKEND_ON.findall(text))
        backend_emit.update(SOCKET_BACKEND_EMIT.findall(text))
    if path.suffix == ".js" or path.suffix == ".html":
        frontend_on.update(SOCKET_FRONTEND_ON.findall(text))
        frontend_emit.update(SOCKET_FRONTEND_EMIT.findall(text))

ignored = {"connect", "disconnect", "connect_error"}

missing_backend = sorted(frontend_emit - backend_on - ignored)
missing_frontend = sorted(backend_emit - frontend_on - ignored)

print("Frontend emite sem listener no backend:")
print("\n".join(f"- {x}" for x in missing_backend) if missing_backend else "OK")

print("\nBackend emite sem listener no frontend:")
print("\n".join(f"- {x}" for x in missing_frontend) if missing_frontend else "OK")

print("\n[8] TEMPLATES REFERENCIADOS PELO FLASK")
render_re = re.compile(r"render_template\(['\"]([^'\"]+)['\"]")
templates_dir = ROOT / "templates"
for path in iter_files():
    if path.suffix == ".py":
        text = read(path)
        for m in render_re.finditer(text):
            template = m.group(1)
            exists = (templates_dir / template).exists()
            if not exists:
                line = text[:m.start()].count("\n") + 1
                print(f"MISSING TEMPLATE: {rel(path)}:{line} -> templates/{template}")
print("Template check finalizado.")

print("\n[9] ASSETS STATIC REFERENCIADOS EM TEMPLATES")
asset_re = re.compile(r"""(?:url_for\(['"]static['"],\s*filename=['"]([^'"]+)['"]\)|['"]/(static/[^'"]+)['"])""")
missing_assets = []
for path in iter_files():
    if path.suffix == ".html":
        text = read(path)
        for m in asset_re.finditer(text):
            asset = m.group(1) or m.group(2)
            asset_path = ROOT / asset if asset.startswith("static/") else ROOT / "static" / asset
            if not asset_path.exists():
                line = text[:m.start()].count("\n") + 1
                missing_assets.append((rel(path), line, str(asset_path.relative_to(ROOT))))

if missing_assets:
    for file, line, asset in missing_assets:
        print(f"MISSING ASSET: {file}:{line} -> {asset}")
else:
    print("OK - nenhum asset faltando detectado.")

print("\n[10] IMPORTS BÁSICOS DO APP")
run_cmd([sys.executable, "- <<PY\nfrom app import app\nprint('APP IMPORT OK')\nprint('routes:', len(app.url_map._rules))\nPY"])

print("\n" + "=" * 80)
print("AUDIT FINALIZADO")
print("=" * 80)
