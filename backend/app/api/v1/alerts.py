"""
Alert endpoints.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.alert import AlertRule, ConditionType
from app.models.asset import Asset, AssetType
from app.schemas.alert import AlertRuleCreate, AlertRuleUpdate, AlertRuleResponse

router = APIRouter()

# Portfolio conditions need a mark across every holding. Volume and market cap
# use the 24h figures already stored on the asset.
_IMPLEMENTED_CONDITIONS = {
    ConditionType.PRICE_ABOVE,
    ConditionType.PRICE_BELOW,
    ConditionType.PERCENT_CHANGE_UP,
    ConditionType.PERCENT_CHANGE_DOWN,
    ConditionType.VOLUME_ABOVE,
    ConditionType.MARKET_CAP_ABOVE,
}


def _coerce_asset_type(raw: str | None) -> AssetType:
    if not raw:
        return AssetType.STOCK
    key = raw.strip().upper().replace("-", "_").replace(" ", "_")
    if key in AssetType.__members__:
        return AssetType[key]
    for member in AssetType:
        if str(member.value).upper() == key:
            return member
    return AssetType.STOCK


async def _resolve_asset_id(db: AsyncSession, alert_data: AlertRuleCreate):
    """Return an assets.id, creating the row from a ticker when needed."""
    if alert_data.asset_id is not None:
        result = await db.execute(select(Asset).filter(Asset.id == alert_data.asset_id))
        existing = result.scalar_one_or_none()
        if existing is None:
            raise HTTPException(status_code=404, detail="Asset not found")
        return existing.id

    symbol = (alert_data.symbol or "").strip().upper()
    if not symbol:
        raise HTTPException(status_code=400, detail="Choose an asset before creating an alert")

    result = await db.execute(select(Asset).filter(Asset.symbol == symbol))
    existing = result.scalar_one_or_none()
    if existing is not None:
        return existing.id

    asset = Asset(
        symbol=symbol,
        name=(alert_data.asset_name or symbol).strip() or symbol,
        asset_type=_coerce_asset_type(alert_data.asset_type),
    )
    db.add(asset)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        result = await db.execute(select(Asset).filter(Asset.symbol == symbol))
        existing = result.scalar_one_or_none()
        if existing is None:
            raise
        return existing.id
    return asset.id


@router.get("/", response_model=List[AlertRuleResponse])
async def get_alerts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all alert rules for current user."""
    result = await db.execute(
        select(AlertRule)
        .filter(AlertRule.user_id == current_user.id)
        .order_by(AlertRule.created_at.desc())
    )
    alerts = result.scalars().all()
    return alerts


@router.post("/", response_model=AlertRuleResponse, status_code=201)
async def create_alert(
    alert_data: AlertRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new alert rule."""
    if alert_data.condition_type not in _IMPLEMENTED_CONDITIONS:
        raise HTTPException(
            status_code=400,
            detail="That condition is not evaluated yet. Use a price, percent-change, volume, or market-cap alert.",
        )
    asset_id = await _resolve_asset_id(db, alert_data)
    payload = alert_data.dict(exclude={"symbol", "asset_type", "asset_name"})
    payload["asset_id"] = asset_id
    alert = AlertRule(
        **payload,
        user_id=current_user.id
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert


@router.get("/{alert_id}", response_model=AlertRuleResponse)
async def get_alert(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific alert rule."""
    result = await db.execute(
        select(AlertRule).filter(
            AlertRule.id == alert_id,
            AlertRule.user_id == current_user.id
        )
    )
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    return alert


@router.put("/{alert_id}", response_model=AlertRuleResponse)
async def update_alert(
    alert_id: str,
    alert_update: AlertRuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update an alert rule."""
    result = await db.execute(
        select(AlertRule).filter(
            AlertRule.id == alert_id,
            AlertRule.user_id == current_user.id
        )
    )
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Update fields
    for field, value in alert_update.dict(exclude_unset=True).items():
        setattr(alert, field, value)

    await db.commit()
    await db.refresh(alert)
    return alert


@router.delete("/{alert_id}", status_code=204)
async def delete_alert(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete an alert rule."""
    result = await db.execute(
        select(AlertRule).filter(
            AlertRule.id == alert_id,
            AlertRule.user_id == current_user.id
        )
    )
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    await db.delete(alert)
    await db.commit()
