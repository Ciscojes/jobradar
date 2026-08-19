import time
from collections.abc import Callable
from typing import Any

import requests


RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def get_with_retry(
    url: str,
    *,
    attempts: int = 3,
    backoff_seconds: float = 0.25,
    request_get: Callable[..., Any] | None = None,
    **kwargs: Any,
) -> Any:
    """GET acotado con reintentos para fallos transitorios y respeto de timeout."""
    request_get = request_get or requests.get
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = request_get(url, **kwargs)
            if getattr(response, "status_code", 200) not in RETRYABLE_STATUS_CODES:
                return response
            last_error = requests.HTTPError(f"HTTP transitorio {response.status_code}")
        except requests.RequestException as exc:
            last_error = exc

        if attempt < attempts - 1:
            time.sleep(backoff_seconds * (2**attempt))

    if last_error:
        raise last_error
    raise RuntimeError("La petición HTTP no produjo respuesta")
