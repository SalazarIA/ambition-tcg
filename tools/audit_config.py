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


def audit_config(app):
    errors = []
    warnings = []

    secret_key = app.config.get("SECRET_KEY")
    environment = str(app.config.get("ENVIRONMENT") or "development").lower()
    debug_mode = as_bool(app.config.get("DEBUG_MODE"))
    database_uri = app.config.get("SQLALCHEMY_DATABASE_URI")

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

    if missing_smtp and is_production:
        errors.append(f"SMTP is incomplete in production. Missing: {missing_smtp}")
    elif missing_smtp:
        warnings.append(f"SMTP incomplete locally. Missing: {missing_smtp}")

    if app.config.get("SMTP_USERNAME") and app.config.get("MAIL_FROM"):
        if app.config.get("SMTP_USERNAME") != app.config.get("MAIL_FROM"):
            warnings.append("SMTP_USERNAME and MAIL_FROM are different. Gmail usually requires them to match.")

    if warnings:
        print("CONFIG WARNINGS:")
        for warning in warnings:
            print("-", warning)

    return errors
