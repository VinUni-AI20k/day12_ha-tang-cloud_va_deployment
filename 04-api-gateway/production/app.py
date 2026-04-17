"""
ADVANCED — Full Security Stack

Kết hợp:
  ✅ JWT Authentication
  ✅ Role-based access (user / admin)
  ✅ Rate limiting (sliding window)
  ✅ Cost guard (daily budget)
  ✅ Input validation
  ✅ Security headers

Chạy:
    python app.py

Lấy token:
    curl -X POST http://localhost:8000/auth/token \\
         -H "Content-Type: application/json" \\
         -d '{"username": "student", "password": "demo123"}'

Dùng token:
    curl -H "Authorization: Bearer <token>" \\
         -X POST http://localhost:8000/ask \\
         -H "Content-Type: application/json" \\
         -d '{"question": "what is docker?"}'
"""
import os
import time
import logging
from datetime import datetime, timezone
from contextlib import asynccontextmanager


from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from auth import verify_token, authenticate_user, create_token
from rate_limiter import rate_limiter_user, rate_limiter_admin
from cost_guard import cost_guard
from utils.mock_llm import ask

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Security layer initialized")
    yield
    logger.info("Shutdown")


app = FastAPI(
    title="Agent — Full Security Stack",
    version="3.0.0",
    lifespan=lifespan,
    # ✅ Ẩn /docs trong production
    docs_url="/docs" if os.getenv("ENVIRONMENT") != "production" else None,
)

# ──────────────────────────────────────────────────────────
# Security Middleware
# ──────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Thêm security headers vào mọi response."""
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # Ẩn server info
    if "server" in response.headers:
        del response.headers["server"]
    return response


# ──────────────────────────────────────────────────────────
# Request/Response Models
# ──────────────────────────────────────────────────────────
class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)


class LoginRequest(BaseModel):
    username: str
    password: str


# ──────────────────────────────────────────────────────────
# Auth Endpoints
# ──────────────────────────────────────────────────────────

@app.post("/auth/token")
def login(body: LoginRequest):
    """
    Public endpoint. Đổi username/password lấy JWT token.
    Token hết hạn sau 60 phút.
    """
    user = authenticate_user(body.username, body.password)
    token = create_token(user["username"], user["role"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in_minutes": 60,
        "hint": f"Include in header: Authorization: Bearer {token[:20]}...",
    }


# ──────────────────────────────────────────────────────────
# Protected Agent Endpoint
# ──────────────────────────────────────────────────────────

@app.post("/ask")
async def ask_agent(
    body: AskRequest,
    request: Request,
    user: dict = Depends(verify_token),  # ✅ JWT required
):
    """
    Protected endpoint. Yêu cầu:
    1. Valid JWT token
    2. Trong rate limit
    3. Trong budget
    """
    username = user["username"]
    role = user["role"]

    # ✅ Rate limiting — theo role
    limiter = rate_limiter_admin if role == "admin" else rate_limiter_user
    rate_info = limiter.check(username)

    # ✅ Cost check trước khi gọi LLM
    cost_guard.check_budget(username)

    # Gọi LLM (mock)
    response_text = ask(body.question)

    # ✅ Ghi nhận usage (mock token count)
    input_tokens = len(body.question.split()) * 2
    output_tokens = len(response_text.split()) * 2
    usage = cost_guard.record_usage(username, input_tokens, output_tokens)

    return {
        "question": body.question,
        "answer": response_text,
        "usage": {
            "requests_remaining": rate_info["remaining"],
            "budget_remaining_usd": usage.total_cost_usd,
        },
    }


@app.get("/me/usage")
def my_usage(user: dict = Depends(verify_token)):
    """Xem usage của bản thân."""
    return cost_guard.get_usage(user["username"])


@app.get("/admin/stats")
def admin_stats(user: dict = Depends(verify_token)):
    """Admin only: xem tổng stats."""
    if user["role"] != "admin":
        raise HTTPException(403, "Admin only")
    return {
        "total_users": "N/A (in-memory demo)",
        "global_cost_usd": cost_guard._global_cost,
        "global_budget_usd": cost_guard.global_daily_budget_usd,
    }


# ──────────────────────────────────────────────────────────
# Health Checks (public)
# ──────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok",
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "security": "JWT + RateLimit + CostGuard",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print("\n=== Demo credentials ===")
    print("  student / demo123  (10 req/min, $1/day budget)")
    print("  teacher / teach456 (100 req/min, $1/day budget)")
    print(f"\nDocs: http://localhost:{port}/docs\n")
    uvicorn.run(app, host="0.0.0.0", port=port, reload=True)
