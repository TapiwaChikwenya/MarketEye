"""
Application configuration using Pydantic settings.
"""
import json
from typing import List, Optional

from pydantic import model_validator, validator
from pydantic_settings import BaseSettings

# Dev compose used to default SECRET_KEY to this string. Production must not boot with it.
_INSECURE_SECRET_KEYS = frozenset(
    {
        "super-secret-key-change-in-production",
        "your-super-secret-key-change-this-in-production",
        "your-secret-key-here",
        "changeme",
    }
)


def parse_cors_origins(value: object) -> object:
    """Accept a JSON list or a comma-separated origin list.

    docker-compose used to pass ``["http://localhost:5173","http://localhost:3000"]``.
    Splitting that string on commas produced origins that still wore their
    brackets and quotes, so the browser's Origin never matched.
    """
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    return [item.strip().strip('"').strip("'") for item in text.split(",") if item.strip()]


class Settings(BaseSettings):
    """Application settings."""

    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "MarketEye"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "24/7 Investment Watcher - Monitor markets with intelligent alerts"

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str
    DATABASE_URL_SYNC: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 60

    # Public URL of the SPA (password reset links, etc.)
    FRONTEND_BASE_URL: str = "http://localhost:5173"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    # When True with DEBUG, also allow browser Origin headers from RFC1918 LAN (see main.py regex).
    CORS_ALLOW_LAN_ORIGINS: bool = True

    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v):
        return parse_cors_origins(v)

    @model_validator(mode="after")
    def reject_placeholder_secret_in_production(self):
        if str(self.ENVIRONMENT).lower() == "production" and self.SECRET_KEY.strip() in _INSECURE_SECRET_KEYS:
            raise ValueError(
                "SECRET_KEY is a known placeholder. Set a unique secret before ENVIRONMENT=production."
            )
        return self

    # Twilio
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None

    # Email (SendGrid HTTP API)
    SENDGRID_API_KEY: Optional[str] = None
    SENDGRID_FROM_EMAIL: str = "noreply@marketeye.com"
    SENDGRID_FROM_NAME: str = "MarketEye"
    # Sandbox mode: SendGrid accepts the request and validates everything
    # but does NOT deliver. Useful for CI / smoke tests only.
    SENDGRID_SANDBOX_MODE: bool = False

    # Market Data APIs
    FINNHUB_API_KEY: Optional[str] = None
    ALPHA_VANTAGE_API_KEY: Optional[str] = None
    COINGECKO_API_KEY: Optional[str] = None
    COINCAP_ENABLED: bool = True

    # Provider Resilience
    PROVIDER_CIRCUIT_BREAKER_THRESHOLD: int = 5
    PROVIDER_CIRCUIT_BREAKER_TIMEOUT: int = 60
    CACHE_FRESH_TTL_SECONDS: int = 300   # 5 minutes
    CACHE_STALE_TTL_SECONDS: int = 1800  # 30 minutes

    # Alert Settings
    ALERT_CHECK_INTERVAL_SECONDS: int = 60
    MARKET_DATA_CACHE_TTL_SECONDS: int = 300  # 5 minutes
    MAX_ALERTS_PER_USER: int = 100
    MAX_NOTIFICATIONS_PER_DAY: int = 50

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
