"""
Watchlist schemas.
"""
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, UUID4


class WatchlistBase(BaseModel):
    """Base watchlist schema."""
    name: str
    description: Optional[str] = None


class WatchlistCreate(WatchlistBase):
    """Schema for creating a watchlist."""
    pass


class WatchlistUpdate(BaseModel):
    """Schema for updating a watchlist."""
    name: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None


class WatchlistResponse(WatchlistBase):
    """Schema for watchlist response."""
    id: UUID4
    user_id: UUID4
    sort_order: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class WatchlistWithAssets(WatchlistResponse):
    """Watchlist with associated assets."""
    asset_ids: List[UUID4] = []


class AddAssetToWatchlist(BaseModel):
    """Schema for adding an asset to a watchlist."""
    asset_id: UUID4
    sort_order: Optional[int] = 0


class RemoveAssetFromWatchlist(BaseModel):
    """Schema for removing an asset from a watchlist."""
    asset_id: UUID4
