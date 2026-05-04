from pathlib import Path
import re
import traceback

REPORT = Path("reports/register_audit_report.md")
lines = []

def add(x=""):
    lines.append(str(x))

def section(title):
    add(f"\n## {title}\n")

section("Compile check")
try:
    import py_compile
    py_compile.compile("app.py", doraise=True)
    py_compile.compile("models.py", doraise=True)
    add("OK: app.py/models.py compile")
except Exception:
    add("FAIL:")
    add("```")
    add(traceback.format_exc())
    add("```")

section("Register route source")
text = Path("app.py").read_text(errors="ignore")
m = re.search(r'@app\.route\("/register".*?\ndef register\(\):.*?(?=\n@app\.route|\n@socketio\.on|\Z)', text, re.S)
if m:
    add("```python")
    add(m.group(0))
    add("```")
else:
    add("FAIL: rota /register não encontrada")

section("Suspicious verification leftovers")
for i, line in enumerate(text.splitlines(), 1):
    if any(k in line for k in [
        "send_verification_email",
        "verification_url",
        "verification_token",
        "confirm_email",
        "resend-verification",
        "is_verified",
        "account_status",
    ]):
        add(f"{i}: {line}")

section("Flask test client GET/POST register")
try:
    from app import app, db, User

    with app.app_context():
        client = app.test_client()

        r = client.get("/register", follow_redirects=False)
        add(f"GET /register: {r.status_code} location={r.headers.get('Location')}")

        test_email = "audit_register_test@ambitionzgame.com"
        old = User.query.filter_by(email=test_email).first()
        if old:
            db.session.delete(old)
            db.session.commit()

        payload = {
            "username": "audit_register_test",
            "email": test_email,
            "password": "Audit123",
            "confirm_password": "Audit123",
        }

        r = client.post("/register", data=payload, follow_redirects=False)
        add(f"POST /register: {r.status_code} location={r.headers.get('Location')}")
        body = r.get_data(as_text=True)[:1500]
        add("Response preview:")
        add("```html")
        add(body)
        add("```")

        user = User.query.filter_by(email=test_email).first()
        if user:
            add(f"USER CREATED: id={user.id} email={user.email} verified={user.is_verified} status={user.account_status}")
        else:
            add("USER NOT CREATED")

except Exception:
    add("FAIL test client:")
    add("```")
    add(traceback.format_exc())
    add("```")

section("Recent git diff around app.py")
try:
    import subprocess
    out = subprocess.run(["git", "diff", "--", "app.py"], capture_output=True, text=True, timeout=20)
    add("```diff")
    add(out.stdout[-8000:])
    add(out.stderr)
    add("```")
except Exception:
    add(traceback.format_exc())

REPORT.write_text("\n".join(lines))
print(f"Report written: {REPORT}")
print("\n".join(lines))
