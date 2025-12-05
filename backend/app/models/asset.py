"""
Asset model.
"""
from sqlalchemy import Column, String, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
import enum
from app.db.base import Base


class AssetType(str, enum.Enum):
    """Asset type enumeration."""
    STOCK = "STOCK"
    CRYPTO = "CRYPTO"
    ETF = "ETF"
    MUTUAL_FUND = "MUTUAL_FUND"
    INDEX = "INDEX"


class Asset(Base):
    """Asset model for stocks, crypto, ETFs, etc."""

    __tablename__ = "assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    asset_type = Column(Enum(AssetType), nullable=False)
    exchange = Column(String, nullable=True)  # e.g., NASDAQ, NYSE, Binance
    currency = Column(String, default="USD")

    # Additional metadata
    description = Column(String, nullable=True)
    logo_url = Column(String, nullable=True)

    # Market data cache (updated periodically)
    current_price = Column(String, nullable=True)  # Stored as string to handle precision
    market_cap = Column(String, nullable=True)
    volume_24h = Column(String, nullable=True)
    change_24h = Column(String, nullable=True)
    change_percent_24h = Column(String, nullable=True)
    last_updated = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Asset {self.symbol} ({self.asset_type})>"
