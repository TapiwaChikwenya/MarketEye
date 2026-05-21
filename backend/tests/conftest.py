import os

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("DATABASE_URL_SYNC", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

os.environ["FINNHUB_API_KEY"] = ""
os.environ["ALPHA_VANTAGE_API_KEY"] = ""

from app.services import market_data
from app.api.v1 import public as public_api


@pytest.fixture(autouse=True)
def clear_market_cache():
    """Reset caches, settings, and provider registry between tests."""
    market_data._fallback_cache.clear()
    market_data._redis_client = None
    market_data._settings = None
    if hasattr(market_data.market_data_service, "_registry"):
        market_data.market_data_service._registry = None
    public_api._trending_cache.clear()
    public_api._trending_cache_ts = 0.0
    public_api._trending_cache_hits = 0
    public_api._trending_cache_misses = 0
    yield
    market_data._fallback_cache.clear()
    market_data._redis_client = None
    market_data._settings = None
    if hasattr(market_data.market_data_service, "_registry"):
        market_data.market_data_service._registry = None
    public_api._trending_cache.clear()
    public_api._trending_cache_ts = 0.0
    public_api._trending_cache_hits = 0
    public_api._trending_cache_misses = 0
