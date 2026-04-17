"""
BASIC — Health Check + Graceful Shutdown

Hai tính năng tối thiểu cần có trước khi deploy:
  1. GET /health  — liveness: "agent có còn sống không?"
  2. GET /ready   — readiness: "agent có sẵn sàng nhận request chưa?"
  3. Graceful shutdown: hoàn thành request hiện tại trước khi tắt

Chạy:
    python app.py

Test health check:
    curl http://localhost:8000/health
    curl http://localhost:8000/ready

Simulate shutdown:
    # Trong terminal khác
    kill -SIGTERM <pid>
    # Xem agent log graceful shutdown message
"""
import os
import time
import signal
import logging
from datetime import datetime, timezone
from contextlib import asynccontextmanager


from fastapi import FastAPI, HTTPException
import uvicorn
from utils.mock_llm import ask

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

START_TIME = time.time()
_is_ready = False
_in_flight_requests = 0  # đếm số request đang xử lý


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _is_ready

    # ── Startup ──
    logger.info("Agent starting up...")
    logger.info("Loading model and checking dependencies...")
    time.sleep(0.2)  # simulate startup time
    _is_ready = True
    logger.info("✅ Agent is ready!")

    yield

    # ── Shutdown ──
    _is_ready = False
    logger.info("🔄 Graceful shutdown initiated...")

    # Chờ request đang xử lý hoàn thành (tối đa 30 giây)
    timeout = 30
    elapsed = 0
    while _in_flight_requests > 0 and elapsed < timeout:
        logger.info(f"Waiting for {_in_flight_requests} in-flight requests...")
        time.sleep(1)
        elapsed += 1

    logger.info("✅ Shutdown complete")


app = FastAPI(title="Agent — Health Check Demo", lifespan=lifespan)


@app.middleware("http")
async def track_requests(request, call_next):
    """Theo dõi số request đang xử lý."""
    global _in_flight_requests
    _in_flight_requests += 1
    try:
        response = await call_next(request)
        return response
    finally:
        _in_flight_requests -= 1


# ──────────────────────────────────────────────────────────
# Business Logic
# ──────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "AI Agent with health checks!"}


@app.post("/ask")
async def ask_agent(question: str):
    if not _is_ready:
        raise HTTPException(503, "Agent not ready")
    return {"answer": ask(question)}


# ──────────────────────────────────────────────────────────
# HEALTH CHECKS — Phần quan trọng nhất của file này
# ──────────────────────────────────────────────────────────

@app.get("/health")
def health():
    """
    LIVENESS PROBE — "Agent có còn sống không?"

    Cloud platform (Railway, Render, K8s) gọi endpoint này định kỳ.
    Nếu trả về non-200 hoặc timeout → platform restart container.

    Nên trả về:
    - status: "ok" hoặc "degraded"
    - uptime: seconds
    - version: để biết đang chạy version nào
    """
    uptime = round(time.time() - START_TIME, 1)

    # Kiểm tra dependencies quan trọng
    checks = {}

    # Check memory (ví dụ đơn giản)
    try:
        import psutil
        mem = psutil.virtual_memory()
        checks["memory"] = {
            "status": "ok" if mem.percent < 90 else "degraded",
            "used_percent": mem.percent,
        }
    except ImportError:
        checks["memory"] = {"status": "ok", "note": "psutil not installed"}

    overall_status = "ok" if all(
        v.get("status") == "ok" for v in checks.values()
    ) else "degraded"

    return {
        "status": overall_status,
        "uptime_seconds": uptime,
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }


@app.get("/ready")
def ready():
    """
    READINESS PROBE — "Agent có sẵn sàng nhận request chưa?"

    Load balancer dùng endpoint này để quyết định có route
    traffic vào instance này không.

    Trả về 503 khi:
    - Đang khởi động (model chưa load xong)
    - Đang shutdown
    - Database/dependencies chưa connect
    """
    if not _is_ready:
        raise HTTPException(
            status_code=503,
            detail="Agent not ready. Check back in a few seconds.",
        )
    return {
        "ready": True,
        "in_flight_requests": _in_flight_requests,
    }


# ──────────────────────────────────────────────────────────
# GRACEFUL SHUTDOWN
# ──────────────────────────────────────────────────────────

def shutdown_handler(signum, _frame):
    """
    Handle SIGTERM from container orchestrator.

    1. Stop accepting new requests — set _is_ready = False
       → /ready trả về 503, load balancer ngừng route traffic vào đây
    2. Finish current requests — lifespan chờ _in_flight_requests về 0
    3. Close connections — uvicorn đóng socket sau khi lifespan kết thúc
    4. Exit — uvicorn thoát sau timeout_graceful_shutdown
    """
    global _is_ready
    logger.info(f"Received signal {signum} — initiating graceful shutdown")

    # Bước 1: Ngừng nhận request mới
    _is_ready = False
    logger.info("Stopped accepting new requests (_is_ready = False)")

    # Bước 2-4: uvicorn sẽ gọi lifespan shutdown → chờ in-flight → exit
    # (xem lifespan context manager phía trên)


signal.signal(signal.SIGTERM, shutdown_handler)
signal.signal(signal.SIGINT, shutdown_handler)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting agent on port {port}")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        # ✅ Cho phép graceful shutdown
        timeout_graceful_shutdown=30,
    )
