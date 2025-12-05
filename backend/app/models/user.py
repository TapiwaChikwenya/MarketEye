"""
User model.
"""
from sqlalchemy import Column, String, Boolean, DateTime, Enum, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
import enum
from app.db.base import Base


class ContactMethod(str, enum.Enum):
    """Contact method enumeration."""
    SMS = "SMS"
    CALL = "CALL"
    PUSH = "PUSH"
    EMAIL = "EMAIL"


class SubscriptionTier(str, enum.Enum):
    """Subscription tier enumeration."""
    FREE = "free"
    PRO = "pro"


class User(Base):
    """User model."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    name = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    phone_verified = Column(Boolean, default=False)

    # Preferences
    preferred_contact_method = Column(
        Enum(ContactMethod),
        default=ContactMethod.EMAIL,
        nullable=False
    )
    time_zone = Column(String, default="UTC")

    # Quiet hours
    quiet_hours_enabled = Column(Boolean, default=False)
    quiet_hours_start = Column(Time, nullable=True)
    quiet_hours_end = Column(Time, nullable=True)

    # Subscription
    subscription_tier = Column(
        Enum(SubscriptionTier),
        default=SubscriptionTier.FREE,
        nullable=False
    )

    # Status
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    email_verified = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<User {self.email}>"
