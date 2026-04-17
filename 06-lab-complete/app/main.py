from fastapi import FastAPI, Depends, HTTPException, Header
import uvicorn
import time
import os
from .config import settings
from .auth import verify_api_key
from .rate_limiter import check_rate_limit
from .cost_guard import verify_budget

app = FastAPI(title=settings.app_name)

# Giả lập trạng thái sẵn sàng
app_ready = True

@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name}

@app.get("/ready")
def ready():
    if not app_ready:
        raise HTTPException(status_code=503, detail="Not ready")
    return {"status": "ready"}

@app.post("/ask")
async def ask(
    question: str, 
    user_id: str = Depends(verify_api_key)
):
    # Áp dụng các lớp bảo mật
    check_rate_limit(user_id)
    verify_budget(user_id)
    
    return {
        "answer": f"Production-ready AI response for: {question}",
        "user": user_id,
        "status": "secured"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=settings.port)
