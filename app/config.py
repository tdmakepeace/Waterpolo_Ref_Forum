import os
from pathlib import Path

import yaml


def load_yaml_config(path=None):
    config_path = Path(path or os.environ.get("APP_CONFIG", "config.yml"))
    if not config_path.is_file():
        example = Path("config.example.yml")
        if example.is_file():
            config_path = example
        else:
            return {}
    with config_path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _env_flag(env, key, default=False):
    raw = env.get(key)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def database_uri(yaml_cfg, override=None):
    if override:
        return override
    db = yaml_cfg.get("database") or {}
    user = db.get("username", "forum")
    password = db.get("password", "forum")
    host = db.get("host", "localhost")
    port = db.get("port", 5432)
    name = db.get("name", "waterpolo_forum")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"


class Config:
    def __init__(self, yaml_cfg=None, env=None):
        yaml_cfg = yaml_cfg if yaml_cfg is not None else load_yaml_config()
        env = env if env is not None else os.environ
        self.SECRET_KEY = env.get("SECRET_KEY", "dev-insecure-secret")
        self.SQLALCHEMY_DATABASE_URI = database_uri(
            yaml_cfg, env.get("DATABASE_URL")
        )
        self.SQLALCHEMY_TRACK_MODIFICATIONS = False
        self.WTF_CSRF_ENABLED = True
        self.REMEMBER_COOKIE_DURATION = 60 * 60 * 24 * 7
        # HTTP Docker deploys must not use Secure cookies, or the CSRF token
        # never lands in the session ("The CSRF session token is missing").
        secure_cookies = _env_flag(env, "SESSION_COOKIE_SECURE", False)
        self.SESSION_COOKIE_HTTPONLY = True
        self.SESSION_COOKIE_SAMESITE = "Lax"
        self.SESSION_COOKIE_SECURE = secure_cookies
        self.REMEMBER_COOKIE_SECURE = secure_cookies
        self.REMEMBER_COOKIE_HTTPONLY = True
        self.REMEMBER_COOKIE_SAMESITE = "Lax"
        self.WTF_CSRF_SSL_STRICT = secure_cookies
        self.SITE_TITLE = yaml_cfg.get("site_title") or "LWPL - Referee Forum"
        self.BACKDROP_IMAGE_URL = yaml_cfg.get("backdrop_image_url") or ""
        self.FIRST_ADMIN = yaml_cfg.get("first_admin") or {}
        self.RESET_FIRST_ADMIN_PASSWORD = bool(
            yaml_cfg.get("reset_first_admin_password", False)
        )
        self.YAML_CONFIG = yaml_cfg
