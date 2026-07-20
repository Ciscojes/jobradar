import os
from dataclasses import dataclass
from functools import lru_cache

from .env import load_environment


load_environment()


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    app_env: str
    database_url: str
    secret_key: str
    access_token_expire_minutes: int
    cors_origins: tuple[str, ...]
    trusted_hosts: tuple[str, ...]
    auto_create_tables: bool
    docs_enabled: bool
    auth_rate_limit_requests: int
    auth_rate_limit_window_seconds: int
    log_level: str

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    is_production = app_env == "production"
    raw_origins = os.getenv("BACKEND_CORS_ORIGINS", "*")
    cors_origins = tuple(
        origin.strip()
        for origin in raw_origins.split(",")
        if origin.strip()
    ) or ("*",)
    raw_trusted_hosts = os.getenv("TRUSTED_HOSTS", "*")
    trusted_hosts = tuple(
        host.strip()
        for host in raw_trusted_hosts.split(",")
        if host.strip()
    ) or ("*",)

    secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")
    if is_production and (
        secret_key == "dev-secret-change-me" or len(secret_key) < 32
    ):
        raise RuntimeError("SECRET_KEY debe configurarse con un valor seguro en producción")
    if is_production and "*" in cors_origins:
        raise RuntimeError("BACKEND_CORS_ORIGINS no puede usar '*' en producción")
    if is_production and "*" in trusted_hosts:
        raise RuntimeError("TRUSTED_HOSTS no puede usar '*' en producción")

    return Settings(
        app_env=app_env,
        database_url=os.getenv("DATABASE_URL", "sqlite:///./jobradar.db"),
        secret_key=secret_key,
        access_token_expire_minutes=_get_int("ACCESS_TOKEN_EXPIRE_MINUTES", 60),
        cors_origins=cors_origins,
        trusted_hosts=trusted_hosts,
        auto_create_tables=_get_bool("AUTO_CREATE_TABLES", not is_production),
        docs_enabled=_get_bool("DOCS_ENABLED", not is_production),
        auth_rate_limit_requests=_get_int("AUTH_RATE_LIMIT_REQUESTS", 20),
        auth_rate_limit_window_seconds=_get_int("AUTH_RATE_LIMIT_WINDOW_SECONDS", 60),
        log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
    )
