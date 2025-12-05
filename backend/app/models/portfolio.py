"""
Portfolio models.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.db.base import Base


class Portfolio(Base):
    """Portfolio model (virtual portfolio tracking)."""

    __tablename__ = "portfolios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)

    name = Column(String, default="My Portfolio")

    # Cached calculations (updated periodically)
    total_cost_basis = Column(Numeric(precision=20, scale=2), default=0)
    current_value = Column(Numeric(precision=20, scale=2), default=0)
    unrealized_pnl = Column(Numeric(precision=20, scale=2), default=0)
    unrealized_pnl_percent = Column(Numeric(precision=10, scale=4), default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_calculated_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Portfolio user={self.user_id}>"


class PortfolioHolding(Base):
    """Portfolio holding model."""

    __tablename__ = "portfolio_holdings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id = Column(UUID(as_uuid=True), ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)

    # Position details
    quantity = Column(Numeric(precision=20, scale=8), nullable=False)
    average_cost_basis = Column(Numeric(precision=20, scale=8), nullable=False)
    total_cost_basis = Column(Numeric(precision=20, scale=2), nullable=False)

    # Optional: track individual purchases
    purchase_date = Column(Date, nullable=True)

    # Cached calculations
    current_price = Column(Numeric(precision=20, scale=8), nullable=True)
    current_value = Column(Numeric(precision=20, scale=2), nullable=True)
    unrealized_pnl = Column(Numeric(precision=20, scale=2), nullable=True)
    unrealized_pnl_percent = Column(Numeric(precision=10, scale=4), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<PortfolioHolding asset={self.asset_id} qty={self.quantity}>"
