"""
Portfolio schemas.
"""
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, UUID4


class PortfolioHoldingBase(BaseModel):
    """Base portfolio holding schema."""
    asset_id: UUID4
    quantity: Decimal
    average_cost_basis: Decimal
    purchase_date: Optional[date] = None


class PortfolioHoldingCreate(PortfolioHoldingBase):
    """Schema for creating a portfolio holding."""
    pass


class PortfolioHoldingUpdate(BaseModel):
    """Schema for updating a portfolio holding."""
    quantity: Optional[Decimal] = None
    average_cost_basis: Optional[Decimal] = None


class PortfolioHoldingResponse(PortfolioHoldingBase):
    """Schema for portfolio holding response."""
    id: UUID4
    portfolio_id: UUID4
    total_cost_basis: Decimal
    current_price: Optional[Decimal] = None
    current_value: Optional[Decimal] = None
    unrealized_pnl: Optional[Decimal] = None
    unrealized_pnl_percent: Optional[Decimal] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PortfolioBase(BaseModel):
    """Base portfolio schema."""
    name: str = "My Portfolio"


class PortfolioCreate(PortfolioBase):
    """Schema for creating a portfolio."""
    pass


class PortfolioUpdate(BaseModel):
    """Schema for updating a portfolio."""
    name: Optional[str] = None


class PortfolioResponse(PortfolioBase):
    """Schema for portfolio response."""
    id: UUID4
    user_id: UUID4
    total_cost_basis: Decimal
    current_value: Decimal
    unrealized_pnl: Decimal
    unrealized_pnl_percent: Decimal
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_calculated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PortfolioWithHoldings(PortfolioResponse):
    """Portfolio with holdings."""
    holdings: List[PortfolioHoldingResponse] = []
