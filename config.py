import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change")
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")

    # Limits
    RETENTION_HOURS = int(os.getenv("RETENTION_HOURS", "24"))
    MAX_FILES = int(os.getenv("MAX_FILES", "10"))
    MAX_FILE_MB = int(os.getenv("MAX_FILE_MB", "50"))
    MAX_TOTAL_PAGES = int(os.getenv("MAX_TOTAL_PAGES", "250"))
    MAX_STORAGE_MB_TOTAL = int(os.getenv("MAX_STORAGE_MB_TOTAL", "500"))

    # DB
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///app.sqlite3")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Privacy
    PRIVACY_SALT = os.getenv("PRIVACY_SALT", "change-this-salt")

class ProductionConfig(Config):
    FLASK_ENV = "production"

class DevelopmentConfig(Config):
    FLASK_ENV = "development"
