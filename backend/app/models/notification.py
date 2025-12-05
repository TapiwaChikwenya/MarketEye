"""
Notification log model.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
import enum
from app.db.base import Base


class EventType(str, enum.Enum):
    """Notification event type."""
    ALERT_TRIGGERED = "ALERT_TRIGGERED"
    THRESHOLD_REACHED = "THRESHOLD_REACHED"
    ERROR = "ERROR"
    CALL_FAILED = "CALL_FAILED"
    SMS_SENT = "SMS_SENT"
    EMAIL_SENT = "EMAIL_SENT"
    PUSH_SENT = "PUSH_SENT"


class NotificationStatus(str, enum.Enum):
    """Notification status."""
    SENT = "SENT"
    FAILED = "FAILED"
    QUEUED = "QUEUED"
    PENDING = "PENDING"


class NotificationLog(Base):
    """Notification log model."""

    __tablename__ = "notification_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    alert_id = Column(UUID(as_uuid=True), ForeignKey("alert_rules.id", ondelete="SET NULL"), nullable=True)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True)

    event_type = Column(Enum(EventType), nullable=False)
    status = Column(Enum(NotificationStatus), default=NotificationStatus.PENDING)

    # Message content
    subject = Column(String, nullable=True)
    message = Column(Text, nullable=False)

    # Additional details (errors, provider responses, etc.)
    details = Column(JSONB, nullable=True)

    # Provider info
    provider = Column(String, nullable=True)  # e.g., "twilio", "smtp"
    provider_message_id = Column(String, nullable=True)

    # Retry tracking
    retry_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    sent_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<NotificationLog {self.event_type} status={self.status}>"
