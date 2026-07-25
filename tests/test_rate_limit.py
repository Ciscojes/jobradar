import pytest
from fastapi import HTTPException, Request

from app.config import get_settings
from app.rate_limit import check_rate_limit, limit_sync_attempts


def test_check_rate_limit_rechaza_exceso_de_intentos():
    key = "test-rate-limit"
    check_rate_limit(key, max_requests=2, window_seconds=60)
    check_rate_limit(key, max_requests=2, window_seconds=60)

    with pytest.raises(HTTPException) as exc_info:
        check_rate_limit(key, max_requests=2, window_seconds=60)

    assert exc_info.value.status_code == 429


def test_sync_tiene_limite_independiente(monkeypatch):
    monkeypatch.setenv("SYNC_RATE_LIMIT_REQUESTS", "2")
    monkeypatch.setenv("SYNC_RATE_LIMIT_WINDOW_SECONDS", "60")
    get_settings.cache_clear()
    def request_with_forwarded_ip(value):
        return Request(
            {
                "type": "http",
                "client": ("192.0.2.50", 1234),
                "headers": [(b"x-forwarded-for", value.encode())],
            }
        )

    limit_sync_attempts(request_with_forwarded_ip("198.51.100.1"))
    limit_sync_attempts(request_with_forwarded_ip("198.51.100.2"))
    with pytest.raises(HTTPException) as exc_info:
        limit_sync_attempts(request_with_forwarded_ip("198.51.100.3"))

    assert exc_info.value.status_code == 429
    get_settings.cache_clear()
