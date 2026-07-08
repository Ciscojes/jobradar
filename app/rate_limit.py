import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request, status

from .config import get_settings


_attempts: dict[str, deque[float]] = defaultdict(deque)
_lock = Lock()


def _client_key(request: Request, scope: str) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        host = forwarded_for.split(",", 1)[0].strip()
    elif request.client:
        host = request.client.host
    else:
        host = "unknown"
    return f"{scope}:{host}"


def check_rate_limit(key: str, max_requests: int, window_seconds: int) -> None:
    now = time.monotonic()
    cutoff = now - window_seconds

    with _lock:
        attempts = _attempts[key]
        while attempts and attempts[0] < cutoff:
            attempts.popleft()

        if len(attempts) >= max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Demasiados intentos. Inténtalo de nuevo en unos minutos.",
            )

        attempts.append(now)


def limit_auth_attempts(request: Request) -> None:
    settings = get_settings()
    check_rate_limit(
        _client_key(request, "auth"),
        settings.auth_rate_limit_requests,
        settings.auth_rate_limit_window_seconds,
    )
