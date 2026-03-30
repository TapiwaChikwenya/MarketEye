"""
Price history model for daily OHLCV data.
"""
from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    Enum,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from app.db.base import Base
from app.models.asset import AssetType


class PriceHistory(Base):
    """Daily OHLCV price history, keyed by (symbol, date)."""

    __tablename__ = "price_history"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    symbol = Column(String, nullable=False)
    asset_type = Column(Enum(AssetType), nullable=False)
    date = Column(Date, nullable=False)
    open = Column(Numeric(20, 8), nullable=False)
    high = Column(Numeric(20, 8), nullable=False)
    low = Column(Numeric(20, 8), nullable=False)
    close = Column(Numeric(20, 8), nullable=False)
    volume = Column(Numeric(20, 2), nullable=True)

    __table_args__ = (
        UniqueConstraint("symbol", "date", name="uq_symbol_date"),
        Index("ix_price_history_symbol_date", "symbol", "date"),
    )

    def __repr__(self):
        return f"<PriceHistory {self.symbol} {self.date} close={self.close}>"
