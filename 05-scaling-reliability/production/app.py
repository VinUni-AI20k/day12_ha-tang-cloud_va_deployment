"""
ADVANCED — Stateless Agent với Redis Session

Stateless = agent không giữ state trong memory.
Mọi state (session, conversation history) lưu trong Redis.

Tại sao stateless quan trọng khi scale?
  Instance 1: User A gửi request 1 → lưu session trong memory
  Instance 2: User A gửi request 2 → KHÔNG có session! Bug!

  ✅ Giải pháp: Lưu session trong Redis
  Bất kỳ instance nào cũng đọc được session của user.

Demo:
  docker compose up
  # Sau đó test multi-turn conversation
  python test_stateless.py
"""
import os
import time
import json
import logging
import uuid
from datetime import datetime, timezone
from contextlib import asynccontextmanager


from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from utils.mock_llm import ask

# ── Redis (optional — fallback to in-memory dict nếu không có Redis)
try:
    import redis
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    _redis = redis.from_url(REDIS_URL, decode_responses=True)
    _redis.ping()
    USE_REDIS = True
    print("✅ Connected to Redis")
except Exception:
    USE_REDIS = False
    _memory_store: dict = {}
    print("⚠️  Redis not available — using in-memory store (not scalable!)")


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

START_TIME = time.time()
INSTANCE_ID = os.getenv("INSTANCE_ID", f"instance-{uuid.uuid4().hex[:6]}")


# ──────────────────────────────────────────────────────────
# Session Storage (Redis-backed, Stateless-compatible)
# ──────────────────────────────────────────────────────────

def save_session(session_id: str, data: dict, ttl_seconds: int = 3600):
    """Lưu session vào Redis với TTL."""
    serialized = json.dumps(data)
    if USE_REDIS:
        _redis.setex(f"session:{session_id}", ttl_seconds, serialized)
    else:
        _memory_store[f"session:{session_id}"] = data


def load_session(session_id: str) -> dict:
    """Load session từ Redis."""
    if USE_REDIS:
        data = _redis.get(f"session:{session_id}")
        return json.loads(data) if data else {}
    return _memory_store.get(f"session:{session_id}", {})


def append_to_history(session_id: str, role: str, content: str):
    """Thêm message vào conversation history."""
    session = load_session(session_id)
    history = session.get("history", [])
    history.append({
        "role": role,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    # Giữ tối đa 20 messages (10 turns)
    if len(history) > 20:
        history = history[-20:]
    session["history"] = history
    save_session(session_id, session)
    return history


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting instance {INSTANCE_ID}")
    logger.info(f"Storage: {'Redis ✅' if USE_REDIS else 'In-memory ⚠️'}")
    yield
    logger.info(f"Instance {INSTANCE_ID} shutting down")


app = FastAPI(
    title="Stateless Agent",
    version="4.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    question: str
    session_id: str | None = None  # None = tạo session mới


# ──────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────
# Exercise 5.3: Stateless Design Demo
#
# ❌ Anti-pattern — State trong memory (KHÔNG làm thế này):
#
#   conversation_history = {}
#
#   @app.post("/ask")
#   def ask(user_id: str, question: str):
#       history = conversation_history.get(user_id, [])
#       # Vấn đề: Instance 1 có history của user, Instance 2 thì không!
#
# ✅ Correct — State trong Redis (stateless):
# ──────────────────────────────────────────────────────────

@app.post("/ask")
async def ask_stateless(user_id: str, question: str):
    """
    Stateless /ask endpoint dùng Redis lrange/rpush.
    Bất kỳ instance nào cũng đọc được history của user.
    """
    history_key = f"history:{user_id}"

    # Đọc history từ Redis (không phải từ memory)
    history = _redis.lrange(history_key, 0, -1) if USE_REDIS else []

    # Gọi LLM
    answer = ask(question)

    # Lưu vào Redis (tất cả instances đều thấy)
    if USE_REDIS:
        _redis.rpush(history_key, f"user: {question}")
        _redis.rpush(history_key, f"assistant: {answer}")
        _redis.expire(history_key, 3600)  # TTL 1 giờ

    return {
        "user_id": user_id,
        "question": question,
        "answer": answer,
        "history_length": len(history),
        "served_by": INSTANCE_ID,
        "storage": "redis" if USE_REDIS else "in-memory ⚠️",
    }


@app.post("/chat")
async def chat(body: ChatRequest):
    """
    Multi-turn conversation với session management.

    Gửi session_id trong các request tiếp theo để tiếp tục cuộc trò chuyện.
    Agent có thể chạy trên bất kỳ instance nào — state trong Redis.
    """
    # Tạo hoặc dùng session hiện có
    session_id = body.session_id or str(uuid.uuid4())

    # Thêm câu hỏi vào history
    append_to_history(session_id, "user", body.question)

    # Gọi LLM với context (trong mock, ta chỉ dùng câu hỏi hiện tại)
    session = load_session(session_id)
    history = session.get("history", [])
    answer = ask(body.question)

    # Lưu response vào history
    append_to_history(session_id, "assistant", answer)

    return {
        "session_id": session_id,
        "question": body.question,
        "answer": answer,
        "turn": len([m for m in history if m["role"] == "user"]) + 1,
        "served_by": INSTANCE_ID,  # ← thấy rõ bất kỳ instance nào cũng serve được
        "storage": "redis" if USE_REDIS else "in-memory",
    }


@app.get("/chat/{session_id}/history")
def get_history(session_id: str):
    """Xem conversation history của một session."""
    session = load_session(session_id)
    if not session:
        raise HTTPException(404, f"Session {session_id} not found or expired")
    return {
        "session_id": session_id,
        "messages": session.get("history", []),
        "count": len(session.get("history", [])),
    }


@app.delete("/chat/{session_id}")
def delete_session(session_id: str):
    """Xóa session (user logout)."""
    if USE_REDIS:
        _redis.delete(f"session:{session_id}")
    else:
        _memory_store.pop(f"session:{session_id}", None)
    return {"deleted": session_id}


# ──────────────────────────────────────────────────────────
# Health / Metrics
# ──────────────────────────────────────────────────────────

@app.get("/health")
def health():
    redis_ok = False
    if USE_REDIS:
        try:
            _redis.ping()
            redis_ok = True
        except Exception:
            redis_ok = False

    status = "ok" if (not USE_REDIS or redis_ok) else "degraded"

    return {
        "status": status,
        "instance_id": INSTANCE_ID,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "storage": "redis" if USE_REDIS else "in-memory",
        "redis_connected": redis_ok if USE_REDIS else "N/A",
    }


@app.get("/ready")
def ready():
    if USE_REDIS:
        try:
            _redis.ping()
        except Exception:
            raise HTTPException(503, "Redis not available")
    return {"ready": True, "instance": INSTANCE_ID}


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
