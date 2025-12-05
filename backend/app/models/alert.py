"""
Alert rule model.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Enum, Numeric, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
import enum
from app.db.base import Base


class ConditionType(str, enum.Enum):
    """Alert condition type."""
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    PERCENT_CHANGE_UP = "percent_change_up"
    PERCENT_CHANGE_DOWN = "percent_change_down"
    VOLUME_ABOVE = "volume_above"
    MARKET_CAP_ABOVE = "market_cap_above"
    PORTFOLIO_VALUE_UP = "portfolio_value_up"
    PORTFOLIO_VALUE_DOWN = "portfolio_value_down"


class NotificationChannel(str, enum.Enum):
    """Notification channel."""
    SMS = "SMS"
    CALL = "CALL"
    PUSH = "PUSH"
    EMAIL = "EMAIL"
    MULTI = "MULTI"  # Multiple channels


class RepeatBehavior(str, enum.Enum):
    """Alert repeat behavior."""
    ONE_TIME = "one_time"
    ONCE_PER_DAY = "once_per_day"
    ONCE_PER_HOUR = "once_per_hour"
    UNLIMITED = "unlimited"


class AlertRule(Base):
    """Alert rule model."""

    __tablename__ = "alert_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=True)

    # Alert configuration
    name = Column(String, nullable=True)  # Optional friendly name
    condition_type = Column(Enum(ConditionType), nullable=False)
    threshold_value = Column(Numeric(precision=20, scale=8), nullable=False)
    lookback_period = Column(String, nullable=True)  # e.g., "1d", "1h", "5m"

    # Notification settings
    notification_channel = Column(Enum(NotificationChannel), default=NotificationChannel.EMAIL)
    repeat_behavior = Column(Enum(RepeatBehavior), default=RepeatBehavior.ONE_TIME)

    # State
    is_active = Column(Boolean, default=True)
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    trigger_count = Column(Integer, default=0)

    # Override quiet hours for this alert
    override_quiet_hours = Column(Boolean, default=False)

    # Custom message
    custom_message = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<AlertRule {self.condition_type} for asset={self.asset_id}>"
