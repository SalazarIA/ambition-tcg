import os, json, re
from pathlib import Path

IGNORE = {'.git', '__pycache__', '.venv', 'venv', 'node_modules'}

print("\n===== ESTRUTURA =====")
for p in sorted(Path(".").rglob("*")):
    if any(i in p.parts for i in IGNORE) or not p.is_file(): continue
    print("  " * (len(p.parts)-1) + p.name)

print("\n===== PYTHON =====")
for p in sorted(Path(".").rglob("*.py")):
    if any(i in p.parts for i in IGNORE): continue
    print(f"\n[{p}]")
    for l in p.read_text(errors="ignore").splitlines():
        if re.match(r"^(class|def|import|from)\s", l.strip()):
            print(" ", l.strip()[:100])

print("\n===== JSON =====")
for p in sorted(Path(".").rglob("*.json")):
    if any(i in p.parts for i in IGNORE): continue
    try:
        d = json.loads(p.read_text(errors="ignore"))
        print(f"[{p}] -> {len(d) if isinstance(d, list) else list(d.keys())}")
        if isinstance(d, list) and d: print("  Ex:", json.dumps(d[0], ensure_ascii=False)[:150])
    except: print(f"[{p}] erro")
