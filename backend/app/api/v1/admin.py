"""
Admin-only endpoints (superuser).

User management, aggregates, and operational metrics.
"""
from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_db, get_current_superuser
from app.models.user import User
from app.models.alert import AlertRule
from app.models.watchlist import Watchlist
from app.models.tracked_asset import TrackedAsset
from app.models.notification import NotificationLog
from app.schemas.admin import (
    AdminOverviewResponse,
    AdminStocksUsageResponse,
    AdminSystemHealthResponse,
    AdminUserListResponse,
    AdminUserPatch,
    AdminUserRow,
)
from app.api.v1 import public as public_api

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/overview", response_model=AdminOverviewResponse)
async def admin_overview(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> AdminOverviewResponse:
    """Aggregated usage from the database + public cache counters."""
    users_total = await db.scalar(select(func.count()).select_from(User)) or 0
    users_active = await db.scalar(select(func.count()).select_from(User).where(User.is_active.is_(True))) or 0

    now = datetime.now(timezone.utc)
    since_24h = now - timedelta(hours=24)
    since_7d = now - timedelta(days=7)

    users_new_24h = await db.scalar(
        select(func.count()).select_from(User).where(User.created_at >= since_24h)
    ) or 0
    users_new_7d = await db.scalar(
        select(func.count()).select_from(User).where(User.created_at >= since_7d)
    ) or 0

    alerts_total = await db.scalar(select(func.count()).select_from(AlertRule)) or 0
    alerts_active = await db.scalar(
        select(func.count()).select_from(AlertRule).where(AlertRule.is_active.is_(True))
    ) or 0

    tracked_assets_rows = await db.scalar(select(func.count()).select_from(TrackedAsset)) or 0
    tracked_unique_symbols = await db.scalar(select(func.count(func.distinct(TrackedAsset.symbol)))) or 0

    watchlists_total = await db.scalar(select(func.count()).select_from(Watchlist)) or 0

    notification_logs_24h = await db.scalar(
        select(func.count()).select_from(NotificationLog).where(NotificationLog.created_at >= since_24h)
    ) or 0

    cache_stats = public_api.get_trending_cache_stats()

    return AdminOverviewResponse(
        users_total=int(users_total),
        users_active=int(users_active),
        users_new_24h=int(users_new_24h),
        users_new_7d=int(users_new_7d),
        alerts_total=int(alerts_total),
        alerts_active=int(alerts_active),
        tracked_assets_rows=int(tracked_assets_rows),
        tracked_unique_symbols=int(tracked_unique_symbols),
        watchlists_total=int(watchlists_total),
        notification_logs_24h=int(notification_logs_24h),
        trending_cache_hits=int(cache_stats["hits"]),
        trending_cache_misses=int(cache_stats["misses"]),
    )


@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> AdminUserListResponse:
    """List users (newest first)."""
    limit = min(max(limit, 1), 200)
    total = await db.scalar(select(func.count()).select_from(User)) or 0

    result = await db.execute(
        select(User).order_by(User.created_at.desc()).offset(skip).limit(limit)
    )
    rows = result.scalars().all()

    items: List[AdminUserRow] = []
    for u in rows:
        items.append(
            AdminUserRow(
                id=u.id,
                email=u.email,
                name=u.name,
                is_active=u.is_active,
                is_superuser=u.is_superuser,
                subscription_tier=u.subscription_tier,
                created_at=u.created_at.isoformat() if u.created_at else None,
            )
        )

    return AdminUserListResponse(items=items, total=int(total), skip=skip, limit=limit)


@router.patch("/users/{user_id}", response_model=AdminUserRow)
async def patch_user(
    user_id: str,
    body: AdminUserPatch,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_superuser),
) -> AdminUserRow:
    """Update user flags (active / superuser)."""
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="User not found") from None

    result = await db.execute(select(User).where(User.id == uid))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    super_count = await db.scalar(select(func.count()).select_from(User).where(User.is_superuser.is_(True))) or 0

    if body.is_superuser is False and target.is_superuser and super_count <= 1:
        raise HTTPException(status_code=400, detail="Cannot remove the last superuser")

    if body.is_active is False and target.id == current_admin.id:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account from admin")

    if body.is_superuser is False and target.id == current_admin.id:
        raise HTTPException(status_code=400, detail="You cannot demote yourself")

    if body.is_active is not None:
        target.is_active = body.is_active
    if body.is_superuser is not None:
        target.is_superuser = body.is_superuser

    await db.commit()
    await db.refresh(target)

    return AdminUserRow(
        id=target.id,
        email=target.email,
        name=target.name,
        is_active=target.is_active,
        is_superuser=target.is_superuser,
        subscription_tier=target.subscription_tier,
        created_at=target.created_at.isoformat() if target.created_at else None,
    )


@router.get("/system/health", response_model=AdminSystemHealthResponse)
async def system_health(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> AdminSystemHealthResponse:
    """DB ping, Redis ping, uptime, configured TTLs."""
    started = getattr(request.app.state, "started_at", None) or time.time()
    uptime = time.time() - float(started)

    db_ok = True
    db_ms: float | None = None
    t0 = time.perf_counter()
    try:
        await db.execute(select(func.count()).select_from(User).limit(1))
        db_ms = (time.perf_counter() - t0) * 1000
    except Exception as e:
        logger.exception("DB health check failed: %s", e)
        db_ok = False
        db_ms = None

    redis_ok = False
    redis_ms: float | None = None
    redis_err: str | None = None
    try:
        import redis as redis_lib

        t1 = time.perf_counter()
        r = redis_lib.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        r.ping()
        redis_ms = (time.perf_counter() - t1) * 1000
        redis_ok = True
    except Exception as e:
        redis_err = str(e)

    ttl_seconds: Dict[str, int] = {
        "cache_fresh": settings.CACHE_FRESH_TTL_SECONDS,
        "cache_stale": settings.CACHE_STALE_TTL_SECONDS,
        "market_data_cache": settings.MARKET_DATA_CACHE_TTL_SECONDS,
        "alert_check_interval": settings.ALERT_CHECK_INTERVAL_SECONDS,
        "access_token_expire_minutes": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "password_reset_token_expire_minutes": settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES * 60,
    }

    return AdminSystemHealthResponse(
        uptime_seconds=uptime,
        api_version=settings.VERSION,
        database_latency_ms=db_ms,
        database_ok=db_ok,
        redis_latency_ms=redis_ms,
        redis_ok=redis_ok,
        redis_error=redis_err,
        ttl_seconds=ttl_seconds,
    )


@router.get("/stocks/usage", response_model=AdminStocksUsageResponse)
async def stocks_usage(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> AdminStocksUsageResponse:
    """Most-tracked symbols."""
    unique = await db.scalar(select(func.count(func.distinct(TrackedAsset.symbol)))) or 0

    q = (
        select(TrackedAsset.symbol, func.count().label("cnt"))
        .group_by(TrackedAsset.symbol)
        .order_by(func.count().desc())
        .limit(15)
    )
    result = await db.execute(q)
    top: List[Dict[str, Any]] = [{"symbol": row[0], "track_count": int(row[1])} for row in result.all()]

    return AdminStocksUsageResponse(unique_symbols_tracked=int(unique), top_symbols=top)
