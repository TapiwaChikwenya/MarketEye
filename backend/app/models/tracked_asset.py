"""
User tracked assets model.
"""
from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.db.base import Base
from app.models.asset import AssetType


class TrackedAsset(Base):
    """Model for user's tracked assets - persists across sessions."""

    __tablename__ = "tracked_assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Asset information (stored directly to avoid foreign key complications)
    symbol = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    asset_type = Column(Enum(AssetType), nullable=False)
    exchange = Column(String, nullable=True)
    
    # Timestamps
    tracked_at = Column(DateTime(timezone=True), server_default=func.now())

    # Ensure unique tracking per user per symbol
    __table_args__ = (
        UniqueConstraint('user_id', 'symbol', name='uq_user_tracked_symbol'),
    )

    def __repr__(self):
        return f"<TrackedAsset user={self.user_id} symbol={self.symbol}>"

