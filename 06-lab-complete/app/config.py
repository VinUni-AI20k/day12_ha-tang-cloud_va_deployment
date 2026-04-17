from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    app_name: str = "My Production AI Agent"
    app_version: str = "1.0.0"
    
    # Cấu hình Server
    port: int = int(os.getenv("PORT", 8000))
    agent_api_key: str = os.getenv("AGENT_API_KEY", "default-secret-key")
    
    # Cấu hình Rate Limit
    rate_limit_per_minute: int = 10
    
    # Cấu hình Budget
    monthly_budget_usd: float = 10.0

settings = Settings()
