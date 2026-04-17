from datetime import datetime
from typing import Optional

import redis as redis_lib
from fastapi import HTTPException

from app.config import settings


def check_and_record_cost(
    user_id: str,
    input_tokens: int,
    output_tokens: int,
    redis_client: Optional[redis_lib.Redis],
) -> None:
    cost = (input_tokens / 1000) * 0.00015 + (output_tokens / 1000) * 0.0006
    if redis_client is None:
        return

    month_key = datetime.now().strftime("%Y-%m")
    key = f"cost:{user_id}:{month_key}"
    current = float(redis_client.get(key) or 0)
    if current >= settings.monthly_budget_usd:
        raise HTTPException(402, "Monthly budget exhausted. Try next month.")

    redis_client.incrbyfloat(key, cost)
    redis_client.expire(key, 32 * 24 * 3600)
