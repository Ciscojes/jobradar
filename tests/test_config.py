import pytest

from app.config import get_settings


def test_production_requires_secure_secret_key(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "dev-secret-change-me")

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        get_settings()

    get_settings.cache_clear()


def test_production_rejects_wildcard_cors(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    monkeypatch.setenv("BACKEND_CORS_ORIGINS", "*")
    monkeypatch.setenv("TRUSTED_HOSTS", "api.example.com")

    with pytest.raises(RuntimeError, match="BACKEND_CORS_ORIGINS"):
        get_settings()

    get_settings.cache_clear()


def test_production_rejects_wildcard_trusted_hosts(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    monkeypatch.setenv("BACKEND_CORS_ORIGINS", "https://app.example.com")
    monkeypatch.setenv("TRUSTED_HOSTS", "*")

    with pytest.raises(RuntimeError, match="TRUSTED_HOSTS"):
        get_settings()

    get_settings.cache_clear()


def test_production_accepts_secure_secret_key(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    monkeypatch.setenv("BACKEND_CORS_ORIGINS", "https://app.example.com")
    monkeypatch.setenv("TRUSTED_HOSTS", "api.example.com")

    settings = get_settings()

    assert settings.is_production is True
    assert settings.secret_key == "x" * 32
    assert settings.cors_origins == ("https://app.example.com",)
    assert settings.trusted_hosts == ("api.example.com",)

    get_settings.cache_clear()
