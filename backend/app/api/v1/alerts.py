"""
Alert endpoints.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.alert import AlertRule
from app.schemas.alert import AlertRuleCreate, AlertRuleUpdate, AlertRuleResponse

router = APIRouter()


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
    alert = AlertRule(
        **alert_data.dict(),
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
