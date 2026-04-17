"""
Exercise 4.4: Cost Guard — Budget Protection với Redis

Logic:
- Mỗi user có budget $10/tháng
- Track spending trong Redis theo key: budget:{user_id}:{YYYY-MM}
- Reset tự động đầu tháng (key expire sau 32 ngày)
"""
import redis
from datetime import datetime

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

MONTHLY_BUDGET_USD = 10.0


def check_budget(user_id: str, estimated_cost: float) -> bool:
    """
    Return True nếu còn budget, False nếu vượt.

    - Dùng Redis key: budget:{user_id}:{YYYY-MM}
    - incrbyfloat để cộng dồn chi phí một cách atomic
    - expire 32 ngày để key tự reset sang tháng mới
    """
    month_key = datetime.now().strftime("%Y-%m")
    key = f"budget:{user_id}:{month_key}"

    current = float(r.get(key) or 0)
    if current + estimated_cost > MONTHLY_BUDGET_USD:
        return False

    r.incrbyfloat(key, estimated_cost)
    r.expire(key, 32 * 24 * 3600)  # 32 ngày → tự reset sang tháng mới
    return True


if __name__ == "__main__":
    # Test thủ công
    user = "user_test"
    print(f"Check $5.00:  {check_budget(user, 5.0)}")   # True
    print(f"Check $4.99:  {check_budget(user, 4.99)}")  # True (tổng $9.99)
    print(f"Check $0.02:  {check_budget(user, 0.02)}")  # False (vượt $10)
