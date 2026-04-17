"""
❌ BASIC — Agent "Kiểu Localhost" (Anti-patterns)

Đây là cách KHÔNG NÊN làm. Dùng để so sánh với advanced/.
Hãy đếm bao nhiêu vấn đề bạn tìm được trong file này.
"""
import os

from fastapi import FastAPI
import uvicorn
from utils.mock_llm import ask

app = FastAPI(title="My Agent")

# Thiết lập logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.get("/")
def home():
    return {"message": "Hello! Agent is running on my machine :)"}

@app.get("/health")
def health():
    """Liveness probe cho Cloud Platform."""
    return {"status": "ok"}

@app.post("/ask")
def ask_agent(question: str, x_api_key: str = Header(None)):
    # Bảo mật: Kiểm tra API Key
    if x_api_key != AGENT_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    logger.info(f"Got question: {question}")
    response = ask(question)
    
    logger.info(f"Response: {response}")
    return {"answer": response}


# ❌ Vấn đề 4: Không có health check endpoint
# Nếu agent crash, platform không biết để restart

# ❌ Vấn đề 5: Port cố định — không đọc từ environment
# Trên Railway/Render, PORT được inject qua env var
if __name__ == "__main__":
    print("Starting agent on localhost:8000...")
    uvicorn.run(
        "app:app",
        host="localhost",   # ❌ chỉ chạy được trên local
        port=8000,          # ❌ cứng port
        reload=True         # ❌ debug reload trong production
    )
