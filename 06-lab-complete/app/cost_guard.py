import time
from fastapi import HTTPException
from .config import settings

class CostGuard:
    def __init__(self, monthly_budget: float):
        self.monthly_budget = monthly_budget
        self.usage = {} # user_id: current_cost

    def check(self, user_id: str, estimated_cost: float = 0.01):
        current_cost = self.usage.get(user_id, 0.0)
        
        if current_cost + estimated_cost > self.monthly_budget:
            raise HTTPException(
                status_code=402,
                detail=f"Monthly budget exceeded. Limit: ${self.monthly_budget}"
            )
        
        # Cập nhật chi phí
        self.usage[user_id] = current_cost + estimated_cost

# Khởi tạo instance
cost_guard = CostGuard(monthly_budget=settings.monthly_budget_usd)

def verify_budget(user_id: str):
    cost_guard.check(user_id)
