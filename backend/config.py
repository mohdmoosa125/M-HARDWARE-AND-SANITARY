"""
config.py
---------
Central configuration for the Flask app.
Reads values from the .env file.
"""
import os
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


class Config:
    # Flask secret key (used to sign session cookies)
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")

    # Database — SQLite by default, PostgreSQL if DATABASE_URL is set
    SQLALCHEMY_DATABASE_URI = (
        os.getenv("DATABASE_URL")
        or "sqlite:///" + os.path.join(BASE_DIR, "mhardware.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # File uploads
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024          # 5 MB per request
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

    # AI (optional)
    AI_API_KEY = os.getenv("AI_API_KEY", "")

    # Session cookie safety
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"