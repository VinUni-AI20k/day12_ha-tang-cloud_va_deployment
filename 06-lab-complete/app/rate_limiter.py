import time
from fastapi import HTTPException
from .config import settings

class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}

    def check(self, user_id: str):
        now = time.time()
        if user_id not in self.requests:
            self.requests[user_id] = []
        
        # Chỉ giữ lại các request trong cửa sổ thời gian (window)
        self.requests[user_id] = [t for t in self.requests[user_id] if t > now - self.window_seconds]
        
        if len(self.requests[user_id]) >= self.max_requests:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Max {self.max_requests} requests per minute."
            )
        
        self.requests[user_id].append(now)

# Khởi tạo instance với cấu hình từ settings
limiter = RateLimiter(max_requests=settings.rate_limit_per_minute, window_seconds=60)

def check_rate_limit(user_id: str):
    limiter.check(user_id)
