import os


DEFAULT_SECRET_KEYS = {
    "dev-secret-change-this",
    "change_this_to_a_long_random_secret",
    "change-me",
    "secret",
    "dev",
}


def as_bool(value):
    if isinstance(value, bool):
        return value

    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def cors_is_open(origins):
    if origins == "*":
        return True

    if isinstance(origins, str):
        return origins.strip() == "*"

    return "*" in (origins or [])


def audit_config(app):
    errors = []
    warnings = []

    secret_key = app.config.get("SECRET_KEY")
    environment = str(app.config.get("ENVIRONMENT") or "development").lower()
    debug_mode = as_bool(app.config.get("DEBUG_MODE"))
    database_uri = app.config.get("SQLALCHEMY_DATABASE_URI")
    csrf_enabled = as_bool(app.config.get("WTF_CSRF_ENABLED", True))
    socketio_origins = app.config.get("SOCKETIO_CORS_EFFECTIVE_ORIGINS")

    is_production = environment == "production"

    print("ENVIRONMENT:", environment)
    print("DEBUG_MODE:", debug_mode)
    print("DATABASE URI PREFIX:", str(database_uri).split(":")[0] if database_uri else None)
    print("PRODUCTION MODE:", is_production)

    weak_secret = (
        not secret_key
        or secret_key in DEFAULT_SECRET_KEYS
        or len(str(secret_key)) < 32
    )

    if weak_secret and is_production:
        errors.append("SECRET_KEY is weak/default in production. Set a strong SECRET_KEY in Render.")
    elif weak_secret:
        warnings.append("SECRET_KEY is weak/default locally. Acceptable for local dev, not for production.")

    if is_production and debug_mode:
        errors.append("DEBUG_MODE must be false in production.")

    print("WTF_CSRF_ENABLED:", csrf_enabled)

    if not csrf_enabled:
        if is_production:
            errors.append("WTF_CSRF_ENABLED must be true in production.")
        else:
            warnings.append("CSRF protection is disabled locally. Keep it enabled before release validation.")

    print("SOCKETIO_CORS_EFFECTIVE_ORIGINS:", socketio_origins)

    if cors_is_open(socketio_origins):
        if is_production:
            errors.append("Socket.IO CORS is open in production. Set SOCKETIO_CORS_ALLOWED_ORIGINS to the public game URL.")
        else:
            warnings.append("Socket.IO CORS is open locally. Use explicit origins for release validation.")

    smtp_keys = [
        "SMTP_HOST",
        "SMTP_USERNAME",
        "SMTP_PASSWORD",
        "MAIL_FROM",
    ]

    missing_smtp = []

    for key in smtp_keys:
        value = app.config.get(key)
        print(f"{key} configured:", bool(value))

        if not value:
            missing_smtp.append(key)

    if missing_smtp:
        warnings.append(f"SMTP incomplete. Password reset email will be unavailable. Missing: {missing_smtp}")

    if app.config.get("SMTP_USERNAME") and app.config.get("MAIL_FROM"):
        if app.config.get("SMTP_USERNAME") != app.config.get("MAIL_FROM"):
            warnings.append("SMTP_USERNAME and MAIL_FROM are different. Gmail usually requires them to match.")

    print("DEV_TOOLS_ENABLED:", bool(app.config.get("DEV_TOOLS_ENABLED", False)))

    if is_production and app.config.get("DEV_TOOLS_ENABLED", False):
        warnings.append("DEV_TOOLS_ENABLED is active in production. Use only during controlled beta operations.")

    if warnings:
        print("CONFIG WARNINGS:")
        for warning in warnings:
            print("-", warning)

    return errors
