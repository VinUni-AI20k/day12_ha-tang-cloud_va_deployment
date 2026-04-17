from fastapi import Header, HTTPException
from typing import Optional
from .config import settings

def verify_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    if not x_api_key or x_api_key != settings.AGENT_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    # Trả về dummy user_id dựa vào key trong app thật, ở đây return tĩnh 'user1'
    return "user_from_key"
