"""Admin API schemas."""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, UUID4, ConfigDict

from app.models.user import SubscriptionTier


class AdminUserRow(BaseModel):
    """User row for admin list."""

    id: UUID4
    email: EmailStr
    name: Optional[str] = None
    is_active: bool
    is_superuser: bool
    subscription_tier: SubscriptionTier
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AdminUserListResponse(BaseModel):
    """Paginated users."""

    items: List[AdminUserRow]
    total: int
    skip: int
    limit: int


class AdminUserPatch(BaseModel):
    """Admin update for a user."""

    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None


class AdminOverviewResponse(BaseModel):
    """High-level counts and usage."""

    users_total: int
    users_active: int
    users_new_24h: int
    users_new_7d: int
    alerts_total: int
    alerts_active: int
    tracked_assets_rows: int
    tracked_unique_symbols: int
    watchlists_total: int
    notification_logs_24h: int
    trending_cache_hits: int
    trending_cache_misses: int


class AdminSystemHealthResponse(BaseModel):
    """Process, DB, Redis, configured TTLs."""

    uptime_seconds: float
    api_version: str
    database_latency_ms: Optional[float] = None
    database_ok: bool
    redis_latency_ms: Optional[float] = None
    redis_ok: bool
    redis_error: Optional[str] = None
    ttl_seconds: Dict[str, int]


class AdminStocksUsageResponse(BaseModel):
    """Symbols tracked across users."""

    unique_symbols_tracked: int
    top_symbols: List[Dict[str, Any]]
