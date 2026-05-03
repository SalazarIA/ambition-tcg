from pathlib import Path
import re
import shutil
from datetime import datetime

ROOT = Path(".")
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / "backups" / f"email_delivery_v114_{STAMP}"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

FILES = ["app.py", "services/email_service.py"]

def backup(path: Path):
    if path.exists():
        dest = BACKUP_DIR / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)

def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def write(path: Path, content: str):
    path.write_text(content, encoding="utf-8")

for f in FILES:
    backup(ROOT / f)

app_path = ROOT / "app.py"
app = read(app_path)

# Ensure os is imported.
if "import os" not in app:
    app = app.replace("import json", "import os\nimport json", 1)

# Add SMTP config after app creation/config area.
if 'app.config["SMTP_HOST"]' not in app and "app.config.update(" not in app:
    # Try to insert after Flask app initialization.
    pattern = re.compile(r"(app\s*=\s*Flask\([^)]+\)\n)")
    match = pattern.search(app)

    smtp_config = '''
app.config["SMTP_HOST"] = os.environ.get("SMTP_HOST")
app.config["SMTP_PORT"] = int(os.environ.get("SMTP_PORT", "587"))
app.config["SMTP_USERNAME"] = os.environ.get("SMTP_USERNAME")
app.config["SMTP_PASSWORD"] = os.environ.get("SMTP_PASSWORD")
app.config["SMTP_USE_TLS"] = os.environ.get("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes", "on")
app.config["MAIL_FROM"] = os.environ.get("MAIL_FROM")
'''

    if match:
        app = app[:match.end()] + smtp_config + app[match.end():]
        print("OK: SMTP config inserted after Flask app creation.")
    else:
        print("WARN: Flask app creation not found. SMTP config not inserted.")
elif 'app.config["SMTP_HOST"]' not in app and "app.config.update(" in app:
    # Safer: insert after first app.config.update block end is hard to infer.
    pattern = re.compile(r"(app\s*=\s*Flask\([^)]+\)\n)")
    match = pattern.search(app)

    smtp_config = '''
app.config["SMTP_HOST"] = os.environ.get("SMTP_HOST")
app.config["SMTP_PORT"] = int(os.environ.get("SMTP_PORT", "587"))
app.config["SMTP_USERNAME"] = os.environ.get("SMTP_USERNAME")
app.config["SMTP_PASSWORD"] = os.environ.get("SMTP_PASSWORD")
app.config["SMTP_USE_TLS"] = os.environ.get("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes", "on")
app.config["MAIL_FROM"] = os.environ.get("MAIL_FROM")
'''

    if match:
        app = app[:match.end()] + smtp_config + app[match.end():]
        print("OK: SMTP config inserted after Flask app creation.")
    else:
        print("WARN: Flask app creation not found. SMTP config not inserted.")
else:
    print("OK: SMTP config already present.")

# Fix register flow: capture send result and give honest feedback.
old = '''        send_verification_email(new_user, verification_url)

        print("Verification link:")
        print(verification_url)

        flash("Registered. Check your email for the verification link. If email is not configured, check server logs.")'''

new = '''        sent = send_verification_email(new_user, verification_url)

        print("Verification link:")
        print(verification_url)

        if sent:
            flash("Registered. Check your email for the verification link.")
        else:
            flash("Registered, but email delivery failed. Use resend verification or contact beta support.")'''

if old in app:
    app = app.replace(old, new, 1)
    print("OK: register email send result now handled.")
else:
    # Fallback for exact current structure seen in grep.
    app = app.replace(
        '''        send_verification_email(new_user, verification_url)
        print("Verification link:")
        print(verification_url)
        flash("Registered. Check your email for the verification link. If email is not configured, check server logs.")''',
        '''        sent = send_verification_email(new_user, verification_url)
        print("Verification link:")
        print(verification_url)

        if sent:
            flash("Registered. Check your email for the verification link.")
        else:
            flash("Registered, but email delivery failed. Use resend verification or contact beta support.")''',
        1
    )
    print("OK/WARN: attempted fallback replacement for register email flow.")

write(app_path, app)

# Update branding line in email copy from old Overreach wording.
email_path = ROOT / "services/email_service.py"
email = read(email_path)
email = email.replace("Risk. Elements. Overreach.", "Risk. Elements. Ambition.")
write(email_path, email)
print("OK: email copy updated.")

print(f"Backup created at: {BACKUP_DIR}")
