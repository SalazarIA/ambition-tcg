import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import app, User

REQUIRED_ADMIN_ROUTES = [
    "/admin",
    "/admin/dev-tools",
    "/admin/system",
    "/admin/release-candidate",
    "/admin/users",
    "/admin/beta-events",
    "/admin/feedback",
    "/admin/reports",
    "/admin/balance",
    "/admin/whoami",
    "/admin/ping",
]

with app.app_context():
    print("=== ADMIN USERS ===")
    admins = User.query.filter_by(is_admin=True).all()
    if not admins:
        print("FAIL: nenhum admin encontrado")
    else:
        for u in admins:
            print(
                f"OK ADMIN id={u.id} email={u.email} username={u.username} "
                f"active={u.account_status == 'active'} status={u.account_status}"
            )

    print("\n=== ADMIN ROUTES ===")
    routes = {str(rule) for rule in app.url_map.iter_rules()}
    ok = True

    for route in REQUIRED_ADMIN_ROUTES:
        if route in routes:
            print("OK:", route)
        else:
            print("FAIL:", route)
            ok = False

    print("\n=== RESULT ===")
    print("ADMIN_STABILITY_OK:", ok and bool(admins))
