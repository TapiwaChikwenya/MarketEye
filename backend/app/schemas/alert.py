"""
Alert schemas.
"""
from typing import Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, UUID4
from app.models.alert import ConditionType, NotificationChannel, RepeatBehavior


class AlertRuleBase(BaseModel):
    """Base alert rule schema."""
    asset_id: Optional[UUID4] = None
    name: Optional[str] = None
    condition_type: ConditionType
    threshold_value: Decimal
    lookback_period: Optional[str] = None
    notification_channel: NotificationChannel = NotificationChannel.EMAIL
    repeat_behavior: RepeatBehavior = RepeatBehavior.ONE_TIME
    override_quiet_hours: bool = False
    custom_message: Optional[str] = None


class AlertRuleCreate(AlertRuleBase):
    """Schema for creating an alert rule."""
    pass


class AlertRuleUpdate(BaseModel):
    """Schema for updating an alert rule."""
    name: Optional[str] = None
    threshold_value: Optional[Decimal] = None
    notification_channel: Optional[NotificationChannel] = None
    repeat_behavior: Optional[RepeatBehavior] = None
    is_active: Optional[bool] = None
    override_quiet_hours: Optional[bool] = None
    custom_message: Optional[str] = None


class AlertRuleResponse(AlertRuleBase):
    """Schema for alert rule response."""
    id: UUID4
    user_id: UUID4
    is_active: bool
    last_triggered_at: Optional[datetime] = None
    trigger_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
