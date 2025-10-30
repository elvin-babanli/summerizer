# config.py
import os

# Layihə kökü (Render-da da işləyir)
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..")) if os.path.basename(HERE) == "app" else HERE

# DB qovluğu: /opt/render/project/src/instance
DB_DIR = os.environ.get("DB_DIR", os.path.join(ROOT, "instance"))
os.makedirs(DB_DIR, exist_ok=True)  # qovluğu YARAT

# Absolute SQLite yolu (+ check_same_thread=False təhlükəsizliyi)
SQLITE_PATH = os.path.join(DB_DIR, "app.db")
SQLITE_URI = f"sqlite:///{SQLITE_PATH}?check_same_thread=False"


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

    # SQLAlchemy (absolute URI; DATABASE_URL varsa onu işlət, yoxdursa SQLite)
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", SQLITE_URI)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"check_same_thread": False}  # SQLite üçün təhlükəsiz
    }
