from pathlib import Path


REQUIRED_FILES = [
    "app.py",
    "models.py",
    "config.py",
    "services/email_service.py",
    "templates/index.html",
    "templates/login.html",
    "templates/register.html",
    "templates/arena.html",
    "templates/admin_dev_tools.html",
    "templates/terms.html",
    "templates/privacy.html",
    "static/css/style.css",
    "static/js/game.js",
    "static/js/card_ui_v103.js",
    "static/js/ambitionz_dom.js",
    "services/admin/cleanup_service.py",
    "services/security/admin_security.py",
    "services/database/schema_tools.py",
    "services/match_telemetry.py",
    "tools/match_telemetry_report.py",
    "services/battle_summary.py",
    "services/reward_tuning.py",
    "tools/rewards_report.py",
    "routes/__init__.py",
    "routes/public.py",
    "routes/auth.py",
    "routes/admin.py",
    "routes/game.py",
    "sockets/__init__.py",
    "sockets/game_socket.py",
    "docs/DATABASE_MIGRATIONS.md",
    "game/card_identity.py",
    "tools/card_identity_report.py",
    "game/progression_loop.py",
    "tools/progression_loop_report.py",
    "game/card_identity_applied.py",
    "tools/applied_card_identity_report.py",
    "templates/progression.html",
    "templates/admin_reports.html",
    "templates/admin_balance.html",
    "static/manifest.webmanifest",
]


def audit_files():
    errors = []

    for file_path in REQUIRED_FILES:
        path = Path(file_path)

        if not path.exists():
            errors.append(f"Missing required file: {file_path}")
            print("FILE MISSING:", file_path)
        else:
            print("FILE OK:", file_path)

    return errors
