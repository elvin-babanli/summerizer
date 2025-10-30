# app/config.py
import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    # Referrer/Origin tələbini yumşaldır:
    WTF_CSRF_SSL_STRICT = False
    WTF_CSRF_CHECK_ORIGIN = False

    # Deploy üçün məntiqli cookie/security parametrləri
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PREFERRED_URL_SCHEME = "https"


class ProductionConfig:
    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")

    # Uploads
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")

    # Limits
    MAX_FILES = int(os.getenv("MAX_FILES", 10))
    MAX_FILE_MB = int(os.getenv("MAX_FILE_MB", 50))
    MAX_TOTAL_PAGES = int(os.getenv("MAX_TOTAL_PAGES", 250))
    RETENTION_HOURS = int(os.getenv("RETENTION_HOURS", 24))
    MAX_STORAGE_MB_TOTAL = int(os.getenv("MAX_STORAGE_MB_TOTAL", 1024)) 

    # Privacy
    PRIVACY_SALT = os.getenv("PRIVACY_SALT", "change-me-salt")

    # SQLAlchemy (əgər DB istifadə edirsənsə)
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///instance/app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
