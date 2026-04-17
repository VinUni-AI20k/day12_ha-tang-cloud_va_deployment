"""Sliding window rate limiter — in-memory per user_id."""
import time
from collections import defaultdict, deque
from fastapi import HTTPException
from app.config import settings

_windows: dict[str, deque] = defaultdict(deque)


def check_rate_limit(user_id: str):
    """Raise 429 if user exceeded rate_limit_per_minute requests in last 60s."""
    now = time.time()
    window = _windows[user_id]
    while window and window[0] < now - 60:
        window.popleft()
    remaining = settings.rate_limit_per_minute - len(window)
    if remaining <= 0:
        retry_after = int(60 - (now - window[0]))
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "limit": settings.rate_limit_per_minute,
                "window_seconds": 60,
                "retry_after_seconds": retry_after,
            },
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(settings.rate_limit_per_minute),
                "X-RateLimit-Remaining": "0",
            },
        )
    window.append(now)
