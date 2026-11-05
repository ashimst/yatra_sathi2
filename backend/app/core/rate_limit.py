"""
Per-client rate limiting as a FastAPI dependency.

Backed by the ``limits`` library. The default ``memory://`` storage is
per-process; set ``RATE_LIMIT_STORAGE_URI=redis://...`` to share counters
across replicas.

Usage::

    @router.post("/chat", dependencies=[rate_limit("ai", settings.RATE_LIMIT_AI)])
"""
import time

from fastapi import Depends, HTTPException, Request, status
from limits import parse
from limits.storage import storage_from_string
from limits.strategies import MovingWindowRateLimiter

from backend.app.config.settings import settings

_storage = storage_from_string(settings.RATE_LIMIT_STORAGE_URI)
_limiter = MovingWindowRateLimiter(_storage)


def _client_key(request: Request) -> str:
    # Behind a proxy, run uvicorn with --proxy-headers so request.client is the
    # real client address (set in the Dockerfile CMD).
    return request.client.host if request.client else "unknown"


def rate_limit(scope: str, limit: str):
    """Return a dependency enforcing ``limit`` (e.g. "20/minute") for ``scope``."""
    item = parse(limit)

    def _dependency(request: Request) -> None:
        if not settings.RATE_LIMIT_ENABLED:
            return
        key = _client_key(request)
        if not _limiter.hit(item, scope, key):
            reset_at, _remaining = _limiter.get_window_stats(item, scope, key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please slow down and try again shortly.",
                headers={"Retry-After": str(max(1, int(reset_at - time.time())))},
            )

    return Depends(_dependency)


def reset_rate_limits() -> None:
    """Clear all counters (used by tests)."""
    _storage.reset()
