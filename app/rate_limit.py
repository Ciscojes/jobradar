import time
import hashlib
from datetime import timedelta
from collections import defaultdict, deque
from threading import Lock

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import models
from .config import get_settings
from .database import get_db


_attempts: dict[str, deque[float]] = defaultdict(deque)
_lock = Lock()


def _client_key(request: Request, scope: str) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for and get_settings().trust_proxy_headers:
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
        for stale_key, stale_attempts in list(_attempts.items()):
            while stale_attempts and stale_attempts[0] < cutoff:
                stale_attempts.popleft()
            if not stale_attempts:
                del _attempts[stale_key]

        attempts = _attempts[key]

        if len(attempts) >= max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Demasiados intentos. Inténtalo de nuevo en unos minutos.",
            )

        attempts.append(now)


def check_persistent_rate_limit(
    db: Session,
    key: str,
    max_requests: int,
    window_seconds: int,
) -> None:
    now = time.time()
    window_id = int(now // window_seconds)
    scope = key.split(":", 1)[0]
    key_hash = hashlib.sha256(key.encode()).hexdigest()

    result = db.execute(
        update(models.RateLimitBucket)
        .where(
            models.RateLimitBucket.scope == scope,
            models.RateLimitBucket.key_hash == key_hash,
            models.RateLimitBucket.window_id == window_id,
            models.RateLimitBucket.request_count < max_requests,
        )
        .values(
            request_count=models.RateLimitBucket.request_count + 1,
            updated_at=models.utc_now(),
        )
    )
    if result.rowcount:
        db.commit()
        return

    try:
        with db.begin_nested():
            db.add(
                models.RateLimitBucket(
                    scope=scope,
                    key_hash=key_hash,
                    window_id=window_id,
                    request_count=1,
                )
            )
            db.flush()
        db.commit()
        return
    except IntegrityError:
        db.rollback()

    result = db.execute(
        update(models.RateLimitBucket)
        .where(
            models.RateLimitBucket.scope == scope,
            models.RateLimitBucket.key_hash == key_hash,
            models.RateLimitBucket.window_id == window_id,
            models.RateLimitBucket.request_count < max_requests,
        )
        .values(
            request_count=models.RateLimitBucket.request_count + 1,
            updated_at=models.utc_now(),
        )
    )
    db.commit()
    if not result.rowcount:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos. Inténtalo de nuevo en unos minutos.",
        )


def _apply_rate_limit(
    db: Session | object,
    key: str,
    max_requests: int,
    window_seconds: int,
) -> None:
    if isinstance(db, Session):
        check_persistent_rate_limit(db, key, max_requests, window_seconds)
    else:
        check_rate_limit(key, max_requests, window_seconds)


def cleanup_rate_limit_buckets(db: Session, retention_hours: int = 48) -> int:
    cutoff = models.utc_now() - timedelta(hours=retention_hours)
    removed = (
        db.query(models.RateLimitBucket)
        .filter(models.RateLimitBucket.updated_at < cutoff)
        .delete(synchronize_session=False)
    )
    db.commit()
    return removed


def limit_auth_attempts(
    request: Request,
    db: Session = Depends(get_db),
) -> None:
    settings = get_settings()
    _apply_rate_limit(
        db,
        _client_key(request, "auth"),
        settings.auth_rate_limit_requests,
        settings.auth_rate_limit_window_seconds,
    )


def limit_sync_attempts(
    request: Request,
    db: Session = Depends(get_db),
) -> None:
    settings = get_settings()
    _apply_rate_limit(
        db,
        _client_key(request, "sync"),
        settings.sync_rate_limit_requests,
        settings.sync_rate_limit_window_seconds,
    )


def limit_user_mutation(
    user_id: int,
    scope: str,
    db: Session | None = None,
) -> None:
    """Limita mutaciones costosas por usuario autenticado."""
    settings = get_settings()
    _apply_rate_limit(
        db,
        f"mutation:{scope}:user:{user_id}",
        settings.mutation_rate_limit_requests,
        settings.mutation_rate_limit_window_seconds,
    )
