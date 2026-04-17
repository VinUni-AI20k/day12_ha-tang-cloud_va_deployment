import time
import os
import signal
import json
import logging
from fastapi import FastAPI, Depends, HTTPException, Header
import uvicorn
from .config import settings
from .auth import verify_api_key
from .rate_limiter import check_rate_limit
from .cost_guard import verify_budget

# Cấu hình Structured Logging (JSON)
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def log_event(event: str, extra: dict = None):
    data = {"event": event, "ts": time.time()}
    if extra:
        data.update(extra)
    logger.info(json.dumps(data))

app = FastAPI(title=settings.app_name)

# Trạng thái sẵn sàng cho Readiness Probe
_is_ready = True

@app.get("/health")
def health():
    return {"status": "ok", "timestamp": time.time()}

@app.get("/ready")
def ready():
    if not _is_ready:
        raise HTTPException(status_code=503, detail="Not ready")
    return {"status": "ready"}

@app.post("/ask")
async def ask(question: str, user_id: str = Depends(verify_api_key)):
    # Áp dụng bảo mật
    check_rate_limit(user_id)
    verify_budget(user_id)
    
    log_event("agent_call", {"user": user_id, "q_len": len(question)})
    
    return {
        "answer": f"Production-ready response for: {question}",
        "user": user_id,
        "status": "secured"
    }

# Xử lý Graceful Shutdown
def handle_sigterm(*args):
    global _is_ready
    _is_ready = False
    log_event("shutdown_signal_received")
    # Đợi một chút để load balancer nhận ra app không còn ready
    time.sleep(2)

signal.signal(signal.SIGTERM, handle_sigterm)

if __name__ == "__main__":
    log_event("startup", {"port": settings.port})
    uvicorn.run(app, host="0.0.0.0", port=settings.port)
