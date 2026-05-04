import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from datetime import datetime, timezone
from app import app, db, User

ADMIN_EMAIL = "admin@ambitionzgame.com"
ADMIN_USERNAME = "ambitionz_admin"
ADMIN_PASSWORD = "Admin123"

with app.app_context():
    db.session.rollback()

    user = User.query.filter_by(email=ADMIN_EMAIL).first()

    if not user:
        username_conflict = User.query.filter_by(username=ADMIN_USERNAME).first()
        if username_conflict:
            username_conflict.username = f"{ADMIN_USERNAME}_old_{username_conflict.id}"
            db.session.commit()

        user = User(
            username=ADMIN_USERNAME,
            email=ADMIN_EMAIL,
            account_status="active",
            is_tester=True,
            is_verified=True,
            verified_at=datetime.now(timezone.utc),
            is_admin=True,
            coins=10000,
            wins=0,
            losses=0,
            xp=0,
            level=1,
        )
        db.session.add(user)
        print("Admin criado.")
    else:
        print("Admin atualizado.")

    user.username = ADMIN_USERNAME
    user.email = ADMIN_EMAIL
    user.set_password(ADMIN_PASSWORD)
    user.is_admin = True
    user.is_tester = True
    user.is_verified = True
    user.account_status = "active"
    user.verified_at = datetime.now(timezone.utc)

    db.session.commit()

    print("ADMIN OK")
    print("Email:", ADMIN_EMAIL)
    print("Senha:", ADMIN_PASSWORD)
    print("ID:", user.id)
    print("Username:", user.username)
    print("is_admin:", user.is_admin)
    print("is_verified:", user.is_verified)
    print("status:", user.account_status)
    print("password_check:", user.check_password(ADMIN_PASSWORD))
