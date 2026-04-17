import time
from fastapi import HTTPException
from app.config import settings
from app.rate_limiter import get_redis_client

def check_and_record_cost(input_tokens: int, output_tokens: int, user_id: str = "global"):
    client = get_redis_client()
    if not client:
        return
        
    today = time.strftime("%Y-%m-%d")
    cost_key = f"daily_cost:{user_id}:{today}"
    
    # Calculate cost (Mock pricing logic from original main.py)
    cost = (input_tokens / 1000) * 0.00015 + (output_tokens / 1000) * 0.0006
    
    current_cost = client.get(cost_key)
    current_cost = float(current_cost) if current_cost else 0.0
    
    if current_cost >= settings.daily_budget_usd:
        raise HTTPException(503, "Daily budget exhausted. Try tomorrow.")
        
    # Atomically increment float in redis
    client.incrbyfloat(cost_key, cost)
    client.expire(cost_key, 86400 * 2) # Keep for 2 days

def get_current_cost(user_id: str = "global") -> float:
    client = get_redis_client()
    if not client:
        return 0.0
    today = time.strftime("%Y-%m-%d")
    cost_key = f"daily_cost:{user_id}:{today}"
    val = client.get(cost_key)
    return float(val) if val else 0.0
