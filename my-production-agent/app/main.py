"""
Production AI Agent that combines the Day 12 deployment concepts.
"""

import json
import logging
import signal
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

import redis as redis_lib
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import check_and_record_cost
from app.rate_limiter import check_rate_limit
from utils.mock_llm import ask as llm_ask


logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format='{"ts":"%(asctime)s","lvl":"%(levelname)s","msg":"%(message)s"}',
)
logger = logging.getLogger(__name__)

START_TIME = time.time()
MAX_HISTORY = 10
_is_ready = False
_request_count = 0
_error_count = 0
_redis: Optional[redis_lib.Redis] = None


def get_redis() -> Optional[redis_lib.Redis]:
    return _redis


def get_history(user_id: str) -> list:
    redis_client = get_redis()
    if redis_client is None:
        return []

    raw = redis_client.lrange(f"history:{user_id}", 0, -1)
    return [json.loads(message) for message in raw]


def save_history(user_id: str, question: str, answer: str) -> None:
    redis_client = get_redis()
    if redis_client is None:
        return

    key = f"history:{user_id}"
    redis_client.rpush(key, json.dumps({"role": "user", "content": question}))
    redis_client.rpush(key, json.dumps({"role": "assistant", "content": answer}))
    redis_client.ltrim(key, -MAX_HISTORY * 2, -1)
    redis_client.expire(key, 7 * 24 * 3600)


@asynccontextmanager
async def lifespan(_: FastAPI):
    global _redis, _is_ready
    logger.info(
        json.dumps(
            {
                "event": "startup",
                "app": settings.app_name,
                "version": settings.app_version,
                "environment": settings.environment,
            }
        )
    )

    if settings.redis_url:
        try:
            _redis = redis_lib.from_url(settings.redis_url, decode_responses=True)
            _redis.ping()
            logger.info(json.dumps({"event": "redis_connected"}))
        except Exception as exc:
            logger.warning(
                json.dumps({"event": "redis_unavailable", "error": str(exc)})
            )
            _redis = None

    _is_ready = True
    logger.info(json.dumps({"event": "ready"}))
    yield
    _is_ready = False

    if _redis:
        _redis.close()

    logger.info(json.dumps({"event": "shutdown"}))


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)


@app.middleware("http")
async def request_middleware(request: Request, call_next):
    global _request_count, _error_count
    start = time.time()
    _request_count += 1

    try:
        response: Response = await call_next(request)
    except Exception:
        _error_count += 1
        raise

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    if "server" in response.headers:
        del response.headers["server"]

    duration = round((time.time() - start) * 1000, 1)
    logger.info(
        json.dumps(
            {
                "event": "request",
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "ms": duration,
            }
        )
    )
    return response


class AskRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100, description="User identifier")
    question: str = Field(..., min_length=1, max_length=2000, description="Your question")


class AskResponse(BaseModel):
    user_id: str
    question: str
    answer: str
    model: str
    history_length: int
    timestamp: str


@app.get("/", tags=["Info"])
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "endpoints": {
            "ask": "POST /ask (requires X-API-Key + user_id)",
            "health": "GET /health",
            "ready": "GET /ready",
        },
    }


@app.post("/ask", response_model=AskResponse, tags=["Agent"])
async def ask_agent(
    body: AskRequest,
    request: Request,
    _key: str = Depends(verify_api_key),
):
    check_rate_limit(body.user_id, get_redis())

    input_tokens = len(body.question.split()) * 2
    check_and_record_cost(body.user_id, input_tokens, 0, get_redis())

    history = get_history(body.user_id)
    logger.info(
        json.dumps(
            {
                "event": "agent_call",
                "user_id": body.user_id,
                "q_len": len(body.question),
                "history_len": len(history),
                "client": str(request.client.host) if request.client else "unknown",
            }
        )
    )

    context = ""
    if history:
        context = "Previous conversation:\n"
        for message in history[-6:]:
            role = "User" if message["role"] == "user" else "Assistant"
            context += f"{role}: {message['content']}\n"
        context += "\nCurrent question: "

    answer = llm_ask(context + body.question)
    save_history(body.user_id, body.question, answer)

    output_tokens = len(answer.split()) * 2
    check_and_record_cost(body.user_id, 0, output_tokens, get_redis())

    return AskResponse(
        user_id=body.user_id,
        question=body.question,
        answer=answer,
        model=settings.llm_model,
        history_length=len(history) // 2,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/health", tags=["Operations"])
def health():
    redis_status = "unavailable"
    if _redis:
        try:
            _redis.ping()
            redis_status = "ok"
        except Exception:
            redis_status = "error"

    return {
        "status": "ok",
        "version": settings.app_version,
        "environment": settings.environment,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "checks": {
            "llm": "mock" if not settings.openai_api_key else "openai",
            "redis": redis_status,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready", tags=["Operations"])
def ready():
    if not _is_ready:
        raise HTTPException(503, "Not ready")
    return {"ready": True}


def _handle_signal(signum, _frame):
    logger.info(json.dumps({"event": "signal", "signum": signum}))


signal.signal(signal.SIGTERM, _handle_signal)
