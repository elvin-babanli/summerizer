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
