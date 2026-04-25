import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "ambition_dev_secret_key_change_later")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///database.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False