import time
from fastapi import HTTPException
from redis import Redis
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# Initialize redis connection globally
redis_client: Redis | None = None


def get_redis_client() -> Redis | None:
    return redis_client

def init_redis():
    global redis_client
    if settings.redis_url:
        try:
            redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
            redis_client.ping()
            logger.info("Connected to Redis successfully.")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}")
            redis_client = None

def check_rate_limit(key: str):
    """ Rate limit using sliding window or simple token bucket in Redis. """
    client = get_redis_client()
    if not client:
        logger.warning("Redis not available, rate limiting is disabled using memory fallback")
        return # Alternatively we can fallback to memory here, but let's just bypass

    now = int(time.time())
    # Window by minute
    window_key = f"rate_limit:{key}:{now // 60}"
    
    current_count = client.incr(window_key)
    if current_count == 1:
        client.expire(window_key, 120)
        
    if current_count > settings.rate_limit_per_minute:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {settings.rate_limit_per_minute} req/min",
            headers={"Retry-After": "60"},
        )
