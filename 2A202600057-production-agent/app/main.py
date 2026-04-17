"""
Production AI Agent — HoDacToan 2A202600057

Features:
  ✅ Config from environment (12-factor)
  ✅ Structured JSON logging
  ✅ API Key authentication
  ✅ Rate limiting (sliding window, 10 req/min)
  ✅ Cost guard (monthly budget, Redis-backed)
  ✅ Conversation history in Redis (stateless)
  ✅ Input validation (Pydantic, 422 on bad input)
  ✅ Health check (liveness) + Readiness probe
  ✅ Graceful shutdown (SIGTERM → drain in-flight)
  ✅ Security headers
  ✅ Secrets from environment only
"""
import json
import signal
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from app.config import settings
from app.auth import verify_api_key
from app.rate_limiter import check_rate_limit
from app.cost_guard import check_budget, estimate_cost

from utils.mock_llm import ask as llm_ask

import logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format='{"ts":"%(asctime)s","lvl":"%(levelname)s","msg":"%(message)s"}',
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
# Redis — conversation history (stateless design)
# ─────────────────────────────────────────────────────────
_redis = None
USE_REDIS = False

try:
    if settings.redis_url:
        import redis as redis_lib
        _r = redis_lib.from_url(settings.redis_url, decode_responses=True)
        _r.ping()
        _redis = _r
        USE_REDIS = True
        logger.info(json.dumps({"event": "redis_connected", "url": settings.redis_url[:20] + "..."}))
except Exception as e:
    logger.warning(json.dumps({"event": "redis_unavailable", "error": str(e)}))

_memory_history: dict[str, list] = {}


def save_history(user_id: str, role: str, content: str):
    key = f"history:{user_id}"
    msg = json.dumps({
        "role": role,
        "content": content,
        "ts": datetime.now(timezone.utc).isoformat(),
    })
    if USE_REDIS:
        _redis.rpush(key, msg)
        _redis.ltrim(key, -20, -1)
        _redis.expire(key, 86400)
    else:
        _memory_history.setdefault(key, []).append(json.loads(msg))
        _memory_history[key] = _memory_history[key][-20:]


def load_history(user_id: str) -> list:
    key = f"history:{user_id}"
    if USE_REDIS:
        return [json.loads(m) for m in (_redis.lrange(key, 0, -1) or [])]
    return _memory_history.get(key, [])


# ─────────────────────────────────────────────────────────
# State
# ─────────────────────────────────────────────────────────
START_TIME = time.time()
_is_ready = False
_in_flight = 0
_request_count = 0


# ─────────────────────────────────────────────────────────
# Lifespan
# ─────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _is_ready
    logger.info(json.dumps({
        "event": "startup",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "storage": "redis" if USE_REDIS else "memory",
    }))
    time.sleep(0.1)
    _is_ready = True
    logger.info(json.dumps({"event": "ready"}))

    yield

    _is_ready = False
    logger.info(json.dumps({"event": "shutdown_start", "in_flight": _in_flight}))
    timeout, elapsed = 30, 0
    while _in_flight > 0 and elapsed < timeout:
        time.sleep(1)
        elapsed += 1
    logger.info(json.dumps({"event": "shutdown_complete"}))


# ─────────────────────────────────────────────────────────
# App
# ─────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)


@app.middleware("http")
async def request_middleware(request: Request, call_next):
    global _request_count, _in_flight
    _request_count += 1
    _in_flight += 1
    start = time.time()
    try:
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        logger.info(json.dumps({
            "event": "request",
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "ms": round((time.time() - start) * 1000, 1),
        }))
        return response
    finally:
        _in_flight -= 1


# ─────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────
class AskRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100, description="Unique user identifier")
    question: str = Field(..., min_length=1, max_length=2000, description="Question for the agent")


class AskResponse(BaseModel):
    user_id: str
    question: str
    answer: str
    history_count: int
    model: str
    timestamp: str


# ─────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────
@app.get("/", tags=["Info"])
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "docs": "/docs",
    }


@app.post("/ask", response_model=AskResponse, tags=["Agent"])
async def ask_agent(
    body: AskRequest,
    _key: str = Depends(verify_api_key),
):
    """
    Send a question to the AI agent.

    Requires `X-API-Key` header. Conversation history is stored per `user_id` in Redis.
    """
    if not _is_ready:
        raise HTTPException(503, "Agent not ready")

    check_rate_limit(body.user_id)

    cost = estimate_cost(body.question)
    check_budget(body.user_id, cost)

    save_history(body.user_id, "user", body.question)
    history = load_history(body.user_id)
    answer = llm_ask(body.question)
    save_history(body.user_id, "assistant", answer)

    logger.info(json.dumps({
        "event": "agent_call",
        "user_id": body.user_id,
        "q_len": len(body.question),
        "history_turns": len(history) // 2,
    }))

    return AskResponse(
        user_id=body.user_id,
        question=body.question,
        answer=answer,
        history_count=len(history) + 1,
        model=settings.llm_model,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/history/{user_id}", tags=["Agent"])
def get_history(user_id: str, _key: str = Depends(verify_api_key)):
    """Retrieve conversation history for a user."""
    history = load_history(user_id)
    return {
        "user_id": user_id,
        "count": len(history),
        "messages": history,
        "storage": "redis" if USE_REDIS else "memory",
    }


@app.get("/health", tags=["Operations"])
def health():
    """Liveness probe — platform restarts container if this fails."""
    return {
        "status": "ok",
        "version": settings.app_version,
        "environment": settings.environment,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "storage": "redis" if USE_REDIS else "memory",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready", tags=["Operations"])
def ready():
    """Readiness probe — load balancer stops routing here if not ready."""
    if not _is_ready:
        raise HTTPException(503, "Not ready — agent is starting up or shutting down")
    return {"ready": True, "in_flight": _in_flight}


@app.get("/metrics", tags=["Operations"])
def metrics(_key: str = Depends(verify_api_key)):
    """Basic metrics endpoint."""
    return {
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "in_flight": _in_flight,
        "storage": "redis" if USE_REDIS else "memory",
    }


# ─────────────────────────────────────────────────────────
# Graceful Shutdown
# ─────────────────────────────────────────────────────────
def _handle_sigterm(signum, _frame):
    global _is_ready
    logger.info(json.dumps({"event": "signal_received", "signum": str(signum)}))
    _is_ready = False


signal.signal(signal.SIGTERM, _handle_sigterm)
# SIGINT (Ctrl+C) để uvicorn tự xử lý — không override


if __name__ == "__main__":
    logger.info(f"Starting {settings.app_name} on {settings.host}:{settings.port}")
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        timeout_graceful_shutdown=30,
    )
