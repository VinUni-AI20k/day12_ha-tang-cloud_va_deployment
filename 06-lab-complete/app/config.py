"""Production config — 12-Factor: tất cả từ environment variables."""
import os
import logging
from dataclasses import dataclass, field

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None


# Local DX: load `.env` automatically when not in production.
# In real deployments (Railway/Render), env vars should be set by the platform.
if os.getenv("ENVIRONMENT", "development") != "production":
    _here = os.path.dirname(__file__)
    _env_path = os.path.abspath(os.path.join(_here, "..", ".env"))
    if load_dotenv is not None:
        load_dotenv(_env_path, override=False)


@dataclass
class Settings:
    # Server
    host: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")

    # App
    app_name: str = field(default_factory=lambda: os.getenv("APP_NAME", "Production AI Agent"))
    app_version: str = field(default_factory=lambda: os.getenv("APP_VERSION", "1.0.0"))

    # LLM (DashScope / Qwen)
    dashscope_endpoint: str = field(default_factory=lambda: os.getenv("DASHSCOPE_ENDPOINT", ""))
    dashscope_api_key: str = field(default_factory=lambda: os.getenv("DASHSCOPE_API_KEY", ""))
    qwen_model: str = field(default_factory=lambda: os.getenv("QWEN_MODEL", "qwen3.5-27b"))

    # Security
    agent_api_key: str = field(default_factory=lambda: os.getenv("AGENT_API_KEY", "dev-key-change-me"))
    jwt_secret: str = field(default_factory=lambda: os.getenv("JWT_SECRET", "dev-jwt-secret"))
    allowed_origins: list = field(
        default_factory=lambda: os.getenv("ALLOWED_ORIGINS", "*").split(",")
    )

    # Rate limiting
    rate_limit_per_minute: int = field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_PER_MINUTE", "20"))
    )

    # Budget
    daily_budget_usd: float = field(
        default_factory=lambda: float(os.getenv("DAILY_BUDGET_USD", "5.0"))
    )

    # Storage
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", ""))

    def validate(self):
        logger = logging.getLogger(__name__)
        if self.environment == "production":
            if self.agent_api_key == "dev-key-change-me":
                raise ValueError("AGENT_API_KEY must be set in production!")
            if self.jwt_secret == "dev-jwt-secret":
                raise ValueError("JWT_SECRET must be set in production!")
        if not self.dashscope_api_key or not self.dashscope_endpoint:
            logger.warning("DashScope env not set (DASHSCOPE_API_KEY/DASHSCOPE_ENDPOINT) — using mock LLM")
        return self


settings = Settings().validate()
