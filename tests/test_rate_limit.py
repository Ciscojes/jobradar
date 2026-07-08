import pytest
from fastapi import HTTPException

from app.rate_limit import check_rate_limit


def test_check_rate_limit_rechaza_exceso_de_intentos():
    key = "test-rate-limit"
    check_rate_limit(key, max_requests=2, window_seconds=60)
    check_rate_limit(key, max_requests=2, window_seconds=60)

    with pytest.raises(HTTPException) as exc_info:
        check_rate_limit(key, max_requests=2, window_seconds=60)

    assert exc_info.value.status_code == 429
