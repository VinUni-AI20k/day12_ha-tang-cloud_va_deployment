"""Sliding window rate limiter — Redis-backed (falls back to in-memory)."""
import time
import uuid
from collections import defaultdict, deque
from typing import Any, Optional
from fastapi import HTTPException
from app.config import settings

import logging
logger = logging.getLogger(__name__)

# ── Redis connection (shared state across instances) ──────────
_redis: Optional[Any] = None
USE_REDIS = False

try:
    if settings.redis_url:
        import redis as redis_lib
        _r = redis_lib.from_url(settings.redis_url, decode_responses=True)
        _r.ping()
        _redis = _r
        USE_REDIS = True
except Exception as e:
    logger.warning(f"Rate limiter: Redis unavailable ({e}), using in-memory fallback")

# ── In-memory fallback (single-instance only) ─────────────────
_windows: dict[str, deque] = defaultdict(deque)

_WINDOW = 60  # seconds


def check_rate_limit(user_id: str):
    """Raise 429 if user exceeded rate_limit_per_minute requests in last 60s."""
    if USE_REDIS:
        _redis_check(user_id)
    else:
        _memory_check(user_id)


def _redis_check(user_id: str):
    """Sliding window via Redis sorted set — works across multiple instances."""
    now = time.time()
    key = f"ratelimit:{user_id}"
    limit = settings.rate_limit_per_minute

    # Cleanup expired entries + count current in one pipeline
    pipe = _redis.pipeline()
    pipe.zremrangebyscore(key, 0, now - _WINDOW)
    pipe.zcard(key)
    _, count = pipe.execute()

    if count >= limit:
        oldest = _redis.zrange(key, 0, 0, withscores=True)
        retry_after = max(1, int(_WINDOW - (now - oldest[0][1]))) if oldest else _WINDOW
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "limit": limit,
                "window_seconds": _WINDOW,
                "retry_after_seconds": retry_after,
            },
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
            },
        )

    # Record this request (unique member to avoid collision under concurrency)
    pipe = _redis.pipeline()
    pipe.zadd(key, {f"{now}:{uuid.uuid4().hex[:8]}": now})
    pipe.expire(key, _WINDOW + 1)
    pipe.execute()


def _memory_check(user_id: str):
    """Sliding window in-memory — single-instance fallback only."""
    now = time.time()
    window = _windows[user_id]
    while window and window[0] < now - _WINDOW:
        window.popleft()
    if len(window) >= settings.rate_limit_per_minute:
        retry_after = max(1, int(_WINDOW - (now - window[0])))
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "limit": settings.rate_limit_per_minute,
                "window_seconds": _WINDOW,
                "retry_after_seconds": retry_after,
            },
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(settings.rate_limit_per_minute),
                "X-RateLimit-Remaining": "0",
            },
        )
    window.append(now)