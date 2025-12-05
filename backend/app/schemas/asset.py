"""
Asset schemas.
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, UUID4
from app.models.asset import AssetType


class AssetBase(BaseModel):
    """Base asset schema."""
    symbol: str
    name: str
    asset_type: AssetType
    exchange: Optional[str] = None
    currency: str = "USD"


class AssetCreate(AssetBase):
    """Schema for creating an asset."""
    pass


class AssetUpdate(BaseModel):
    """Schema for updating an asset."""
    name: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None


class AssetResponse(AssetBase):
    """Schema for asset response."""
    id: UUID4
    description: Optional[str] = None
    logo_url: Optional[str] = None
    current_price: Optional[str] = None
    market_cap: Optional[str] = None
    volume_24h: Optional[str] = None
    change_24h: Optional[str] = None
    change_percent_24h: Optional[str] = None
    last_updated: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AssetSearch(BaseModel):
    """Schema for asset search."""
    query: str
    asset_type: Optional[AssetType] = None
    limit: int = 20
