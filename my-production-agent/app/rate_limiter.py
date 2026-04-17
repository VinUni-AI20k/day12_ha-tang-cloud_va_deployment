import collections
import time
from typing import Optional

import redis as redis_lib
from fastapi import HTTPException

from app.config import settings


_rate_limit_fallback: dict[str, list[float]] = collections.defaultdict(list)


def check_rate_limit(user_id: str, redis_client: Optional[redis_lib.Redis]) -> None:
    now = time.time()
    if redis_client is None:
        timestamps = _rate_limit_fallback[user_id]
        _rate_limit_fallback[user_id] = [t for t in timestamps if now - t < 60]
        _rate_limit_fallback[user_id].append(now)
        if len(_rate_limit_fallback[user_id]) > settings.rate_limit_per_minute:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: {settings.rate_limit_per_minute} req/min",
                headers={"Retry-After": "60"},
            )
        return

    key = f"ratelimit:{user_id}"
    pipe = redis_client.pipeline()
    pipe.zremrangebyscore(key, 0, now - 60)
    pipe.zadd(key, {str(now): now})
    pipe.zcard(key)
    pipe.expire(key, 60)
    results = pipe.execute()
    count = results[2]

    if count > settings.rate_limit_per_minute:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {settings.rate_limit_per_minute} req/min",
            headers={"Retry-After": "60"},
        )
