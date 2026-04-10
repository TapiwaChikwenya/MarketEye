"""
Application configuration using Pydantic settings.
"""
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, validator
import os


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

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    # When True with DEBUG, also allow browser Origin headers from RFC1918 LAN (see main.py regex).
    CORS_ALLOW_LAN_ORIGINS: bool = True

    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v

    # Twilio
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None

    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: str = "noreply@marketeye.com"
    SMTP_FROM_NAME: str = "MarketEye"

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
