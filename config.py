import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")


def normalize_database_url(database_url):
    if not database_url:
        return f"sqlite:///{BASE_DIR / 'instance' / 'database.db'}"

    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql://", 1)

    return database_url


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "ambition_dev_secret_key_change_later")

    DATABASE_URL = normalize_database_url(os.environ.get("DATABASE_URL"))

    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
    DEBUG_MODE = os.environ.get("DEBUG_MODE", "false").lower() == "true"

    PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://127.0.0.1:8080")

    SESSION_COOKIE_NAME = "ambition_session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
    }