from fastapi import Header, HTTPException
from .config import settings

def verify_api_key(x_api_key: str = Header(...)):
    """
    Dependency để kiểm tra API Key từ header.
    """
    if x_api_key != settings.agent_api_key:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Invalid or missing API Key"
        )
    return "authorized_user"
