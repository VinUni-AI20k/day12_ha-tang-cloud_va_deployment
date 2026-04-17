import json
import logging
import signal
import time
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .config import settings
from .auth import verify_api_key
from .rate_limiter import check_rate_limit, r
from .cost_guard import check_budget
from .utils.mock_llm import ask

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(message)s",
)
logger = logging.getLogger(__name__)


def _log(event: str, **kwargs):
    """Structured JSON logging."""
    logger.info(json.dumps({"event": event, **kwargs}))

# State management for graceful shutdown
_is_ready = False
_in_flight_requests = 0

def _sigterm_handler(signum, frame):
    """Handle SIGTERM from container orchestrator — FastAPI lifespan handles the rest."""
    _log("signal_received", signum=signum)


signal.signal(signal.SIGTERM, _sigterm_handler)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _is_ready
    _log("startup", version="1.0.0")
    await asyncio.sleep(0.5)  # simulate warm-up
    _is_ready = True
    _log("ready")

    yield

    # Graceful shutdown: stop taking new requests, wait for in-flight ones
    _is_ready = False
    _log("shutdown_initiated", in_flight=_in_flight_requests)
    shutdown_timeout = 30
    elapsed = 0
    while _in_flight_requests > 0 and elapsed < shutdown_timeout:
        await asyncio.sleep(1)
        elapsed += 1
    _log("shutdown_complete")

app = FastAPI(title="Production Ready AI Agent", lifespan=lifespan)

@app.middleware("http")
async def track_requests(request, call_next):
    global _in_flight_requests
    _in_flight_requests += 1
    start = time.time()
    try:
        response = await call_next(request)
        _log("request",
             method=request.method,
             path=request.url.path,
             status=response.status_code,
             ms=round((time.time() - start) * 1000, 1))
        return response
    finally:
        _in_flight_requests -= 1

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}

@app.get("/ready")
def ready():
    if not _is_ready:
        return JSONResponse(status_code=503, content={"status": "not ready"})
    try:
        r.ping()
        return {"status": "ready"}
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": f"not ready: {str(e)}"})

class AskRequest(BaseModel):
    question: str
    user_id: str
    session_id: str | None = None

@app.post("/ask")
def ask_endpoint(
    body: AskRequest,
    api_key_user: str = Depends(verify_api_key)
    # the auth checking user is not necessarily the request 'user_id' in a generic app,
    # but let's strictly check by the one in payload
):
    if not _is_ready:
        raise HTTPException(status_code=503, detail="Service unavailable.")
        
    check_rate_limit(body.user_id)
    check_budget(body.user_id)
    
    session_id = body.session_id or f"sess_{body.user_id}_{int(time.time())}"
    history_key = f"history:{session_id}"
    
    # Simple history retrieval
    history_json = r.lrange(history_key, 0, -1)
    history = [json.loads(h) for h in history_json]
    
    # Append user question
    r.rpush(history_key, json.dumps({"role": "user", "content": body.question}))
    
    # In reality, pass history to LLM... here just use mock
    answer = ask(body.question)
    
    # Append assistant response
    r.rpush(history_key, json.dumps({"role": "assistant", "content": answer}))
    # Retain for 1 hour
    r.expire(history_key, 3600)
    
    return {
        "session_id": session_id,
        "question": body.question,
        "answer": answer,
        "history_length": len(history) + 2
    }
