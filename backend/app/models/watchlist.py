"""
Watchlist models.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.db.base import Base


class Watchlist(Base):
    """Watchlist model."""

    __tablename__ = "watchlists"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)

    # For ordering watchlists
    sort_order = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Watchlist {self.name}>"


class WatchlistAsset(Base):
    """Association table for watchlist and assets (many-to-many)."""

    __tablename__ = "watchlist_assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    watchlist_id = Column(UUID(as_uuid=True), ForeignKey("watchlists.id", ondelete="CASCADE"), nullable=False)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)

    # For ordering assets within a watchlist
    sort_order = Column(Integer, default=0)

    # Timestamps
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<WatchlistAsset watchlist={self.watchlist_id} asset={self.asset_id}>"
