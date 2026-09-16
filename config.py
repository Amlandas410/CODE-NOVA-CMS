import os


def _env_flag(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "change-me-in-production")
    DEBUG = _env_flag("FLASK_DEBUG", False)
    ENV = "development" if DEBUG else "production"
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))
    MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "code_nova_cms")
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_SSL = _env_flag("MYSQL_SSL", False)
    MYSQL_SSL_CA = os.getenv("MYSQL_SSL_CA", "")
    JSON_SORT_KEYS = False
    SESSION_COOKIE_SECURE = _env_flag("SESSION_COOKIE_SECURE", not DEBUG)
    SESSION_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = int(os.getenv("PERMANENT_SESSION_LIFETIME", "604800"))
    SESSION_COOKIE_SAMESITE = "Lax"
