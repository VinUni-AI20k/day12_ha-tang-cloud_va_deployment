"""Monthly budget guard — tracks spending per user in Redis (or in-memory fallback)."""
import logging
from datetime import datetime
from fastapi import HTTPException
from app.config import settings

logger = logging.getLogger(__name__)

_redis = None
USE_REDIS = False

try:
    if settings.redis_url:
        import redis as redis_lib
        _r = redis_lib.from_url(settings.redis_url, decode_responses=True)
        _r.ping()
        _redis = _r
        USE_REDIS = True
except Exception as e:
    logger.warning(f"Cost guard: Redis unavailable ({e}), using in-memory fallback")

_memory_cost: dict[str, float] = {}

COST_PER_INPUT_TOKEN = 0.00000015   # $0.15 / 1M tokens
COST_PER_OUTPUT_TOKEN = 0.0000006   # $0.60 / 1M tokens


def estimate_cost(question: str, answer: str = "") -> float:
    input_tokens = len(question.split()) * 2
    output_tokens = len(answer.split()) * 2
    return input_tokens * COST_PER_INPUT_TOKEN + output_tokens * COST_PER_OUTPUT_TOKEN


def check_budget(user_id: str, estimated_cost: float):
    """Raise 402 if user's monthly budget is exhausted. Deduct cost if OK."""
    month_key = datetime.now().strftime("%Y-%m")
    key = f"budget:{user_id}:{month_key}"

    if USE_REDIS:
        current = float(_redis.get(key) or 0)
        if current + estimated_cost > settings.monthly_budget_usd:
            raise HTTPException(
                402,
                detail={
                    "error": "Monthly budget exhausted",
                    "budget_usd": settings.monthly_budget_usd,
                    "spent_usd": round(current, 6),
                    "user_id": user_id,
                },
            )
        _redis.incrbyfloat(key, estimated_cost)
        _redis.expire(key, 32 * 24 * 3600)
    else:
        current = _memory_cost.get(key, 0.0)
        if current + estimated_cost > settings.monthly_budget_usd:
            raise HTTPException(
                402,
                detail={
                    "error": "Monthly budget exhausted",
                    "budget_usd": settings.monthly_budget_usd,
                    "spent_usd": round(current, 6),
                    "user_id": user_id,
                },
            )
        _memory_cost[key] = current + estimated_cost
