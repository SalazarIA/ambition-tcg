import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-this")

    ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
    DEBUG_MODE = os.environ.get("DEBUG_MODE", "false").lower() == "true"

    PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://127.0.0.1:8080")

    raw_database_url = os.environ.get("DATABASE_URL")

    if raw_database_url:
        SQLALCHEMY_DATABASE_URI = raw_database_url
    else:
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{INSTANCE_DIR / 'database.db'}"

    if SQLALCHEMY_DATABASE_URI == "sqlite:///instance/database.db":
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{INSTANCE_DIR / 'database.db'}"

    if SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
            "postgres://",
            "postgresql://",
            1,
        )

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
