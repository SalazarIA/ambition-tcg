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

    # Corrige SQLite relativo problemático no Flask-SQLAlchemy
    if url in {
        "sqlite:///instance/database.db",
        "sqlite://instance/database.db",
        "sqlite:///./instance/database.db",
    }:
        return f"sqlite:///{LOCAL_SQLITE_PATH}"

    return url


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-this")

    ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
    DEBUG_MODE = os.environ.get("DEBUG_MODE", "false").lower() == "true"

    PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://127.0.0.1:8080")

    cleaned_database_url = clean_database_url(os.environ.get("DATABASE_URL"))

    if cleaned_database_url:
        SQLALCHEMY_DATABASE_URI = cleaned_database_url
    else:
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{LOCAL_SQLITE_PATH}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"

    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE

    MAX_CONTENT_LENGTH = 2 * 1024 * 1024

    WTF_CSRF_ENABLED = False

    LOGIN_ATTEMPT_LIMIT = int(os.environ.get("LOGIN_ATTEMPT_LIMIT", "8"))
    FEEDBACK_DAILY_LIMIT = int(os.environ.get("FEEDBACK_DAILY_LIMIT", "10"))
