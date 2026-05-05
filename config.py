import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(parents=True, exist_ok=True)

LOCAL_SQLITE_PATH = INSTANCE_DIR / "database.db"


def clean_database_url(raw_url):
    if not raw_url:
        return None

    url = str(raw_url).strip().strip('"').strip("'")

    invalid_values = {
        "",
        "<postgresql internal database url>",
        "<postgres internal database url>",
        "postgresql internal database url",
        "postgres internal database url",
    }

    if url.lower() in invalid_values:
        return None

    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    if url in {
        "sqlite:///instance/database.db",
        "sqlite://instance/database.db",
        "sqlite:///./instance/database.db",
    }:
        return f"sqlite:///{LOCAL_SQLITE_PATH}"

    return url


def as_bool(value, default=False):
    if value is None:
        return default

    if isinstance(value, bool):
        return value

    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def parse_csv_env(value):
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


class Config:

    DEV_TOOLS_ENABLED = os.environ.get("DEV_TOOLS_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
    ADMIN_DANGER_CONFIRMATION = os.environ.get("ADMIN_DANGER_CONFIRMATION", "RESET AMBITIONZ")
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-this")

    ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
    DEBUG_MODE = as_bool(os.environ.get("DEBUG_MODE"), default=False)

    PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://127.0.0.1:8080")

    cleaned_database_url = clean_database_url(os.environ.get("DATABASE_URL"))

    if cleaned_database_url:
        SQLALCHEMY_DATABASE_URI = cleaned_database_url
    else:
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{LOCAL_SQLITE_PATH}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
    SESSION_COOKIE_SECURE = as_bool(os.environ.get("SESSION_COOKIE_SECURE"), default=False)

    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE

    MAX_CONTENT_LENGTH = 2 * 1024 * 1024

    WTF_CSRF_ENABLED = as_bool(os.environ.get("WTF_CSRF_ENABLED"), default=True)
    EMAIL_LOG_BODY_ENABLED = as_bool(os.environ.get("EMAIL_LOG_BODY_ENABLED"), default=False)

    LOGIN_ATTEMPT_LIMIT = int(os.environ.get("LOGIN_ATTEMPT_LIMIT", "8"))
    LOGIN_ATTEMPT_WINDOW_MINUTES = int(os.environ.get("LOGIN_ATTEMPT_WINDOW_MINUTES", "15"))
    FEEDBACK_DAILY_LIMIT = int(os.environ.get("FEEDBACK_DAILY_LIMIT", "10"))
    PASSWORD_MIN_LENGTH = int(os.environ.get("PASSWORD_MIN_LENGTH", "10"))
    PASSWORD_REQUIRE_COMPLEXITY = as_bool(os.environ.get("PASSWORD_REQUIRE_COMPLEXITY"), default=True)
    MATCHMAKING_BOT_FALLBACK_SECONDS = float(os.environ.get("MATCHMAKING_BOT_FALLBACK_SECONDS", "10"))

    BETA_INVITE_REQUIRED = as_bool(os.environ.get("BETA_INVITE_REQUIRED"), default=False)
    BETA_AUTO_VERIFY = as_bool(os.environ.get("BETA_AUTO_VERIFY"), default=True)
    SOCKETIO_CORS_ALLOWED_ORIGINS = os.environ.get("SOCKETIO_CORS_ALLOWED_ORIGINS", "")

    SMTP_HOST = os.environ.get("SMTP_HOST", "")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    SMTP_USE_TLS = as_bool(os.environ.get("SMTP_USE_TLS"), default=True)
    MAIL_FROM = os.environ.get("MAIL_FROM", SMTP_USERNAME or "no-reply@ambition-tcg.local")

    @classmethod
    def smtp_enabled(cls):
        return bool(cls.SMTP_HOST and cls.SMTP_USERNAME and cls.SMTP_PASSWORD and cls.MAIL_FROM)

    @classmethod
    def socketio_cors_allowed_origins(cls):
        configured_origins = parse_csv_env(cls.SOCKETIO_CORS_ALLOWED_ORIGINS)

        if configured_origins:
            if configured_origins == ["*"]:
                return "*"

            return configured_origins

        default_origins = [cls.PUBLIC_BASE_URL.rstrip("/")]

        if str(cls.ENVIRONMENT).lower() != "production":
            default_origins.extend([
                "http://127.0.0.1:8080",
                "http://localhost:8080",
                "http://127.0.0.1:5000",
                "http://localhost:5000",
            ])

        return sorted(set(default_origins))


# Ambitionz security/admin controls
DEV_TOOLS_ENABLED = as_bool(os.environ.get("DEV_TOOLS_ENABLED"), default=False)
ADMIN_DANGER_CONFIRMATION = os.environ.get("ADMIN_DANGER_CONFIRMATION", "RESET AMBITIONZ")
