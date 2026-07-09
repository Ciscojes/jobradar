import pytest

from app.config import get_settings


def test_production_requires_secure_secret_key(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "dev-secret-change-me")

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        get_settings()

    get_settings.cache_clear()


def test_production_accepts_secure_secret_key(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "x" * 32)

    settings = get_settings()

    assert settings.is_production is True
    assert settings.secret_key == "x" * 32

    get_settings.cache_clear()
