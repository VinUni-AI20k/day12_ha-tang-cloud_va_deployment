from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PORT: int = 8000
    REDIS_URL: str = "redis://localhost:6379/0"
    AGENT_API_KEY: str = "secret"
    LOG_LEVEL: str = "INFO"
    RATE_LIMIT_PER_MINUTE: int = 10
    MONTHLY_BUDGET_USD: float = 10.0

    class Config:
        env_file = ".env"

settings = Settings()
