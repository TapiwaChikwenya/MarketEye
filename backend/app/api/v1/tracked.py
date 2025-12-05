"""
Tracked assets endpoints - persistent user tracking.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pydantic import BaseModel
from datetime import datetime
from app.core.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.tracked_asset import TrackedAsset
from app.models.asset import AssetType

router = APIRouter()


class TrackedAssetCreate(BaseModel):
    """Schema for tracking an asset."""
    symbol: str
    name: str
    asset_type: str  # STOCK, CRYPTO, ETF, MUTUAL_FUND, INDEX
    exchange: Optional[str] = None


class TrackedAssetResponse(BaseModel):
    """Schema for tracked asset response."""
    id: str
    symbol: str
    name: str
    asset_type: str
    exchange: Optional[str]
    tracked_at: datetime

    class Config:
        from_attributes = True


@router.get("/", response_model=List[TrackedAssetResponse])
async def get_tracked_assets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all tracked assets for current user."""
    result = await db.execute(
        select(TrackedAsset)
        .filter(TrackedAsset.user_id == current_user.id)
        .order_by(TrackedAsset.tracked_at.desc())
    )
    tracked = result.scalars().all()
    
    return [
        TrackedAssetResponse(
            id=str(t.id),
            symbol=t.symbol,
            name=t.name,
            asset_type=t.asset_type.value if hasattr(t.asset_type, 'value') else str(t.asset_type),
            exchange=t.exchange,
            tracked_at=t.tracked_at
        )
        for t in tracked
    ]


@router.post("/", response_model=TrackedAssetResponse, status_code=201)
async def track_asset(
    asset_data: TrackedAssetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Track a new asset."""
    # Check if already tracked
    result = await db.execute(
        select(TrackedAsset).filter(
            TrackedAsset.user_id == current_user.id,
            TrackedAsset.symbol == asset_data.symbol.upper()
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(status_code=400, detail="Asset already tracked")
    
    # Parse asset type
    try:
        asset_type = AssetType[asset_data.asset_type.upper()]
    except KeyError:
        asset_type = AssetType.STOCK  # Default to stock
    
    # Create tracked asset
    tracked = TrackedAsset(
        user_id=current_user.id,
        symbol=asset_data.symbol.upper(),
        name=asset_data.name,
        asset_type=asset_type,
        exchange=asset_data.exchange
    )
    
    db.add(tracked)
    await db.commit()
    await db.refresh(tracked)
    
    return TrackedAssetResponse(
        id=str(tracked.id),
        symbol=tracked.symbol,
        name=tracked.name,
        asset_type=tracked.asset_type.value,
        exchange=tracked.exchange,
        tracked_at=tracked.tracked_at
    )


@router.delete("/{symbol}", status_code=204)
async def untrack_asset(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Stop tracking an asset."""
    result = await db.execute(
        select(TrackedAsset).filter(
            TrackedAsset.user_id == current_user.id,
            TrackedAsset.symbol == symbol.upper()
        )
    )
    tracked = result.scalar_one_or_none()
    
    if not tracked:
        raise HTTPException(status_code=404, detail="Tracked asset not found")
    
    await db.delete(tracked)
    await db.commit()


@router.post("/sync", response_model=List[TrackedAssetResponse])
async def sync_tracked_assets(
    assets: List[TrackedAssetCreate],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Sync tracked assets from client - useful for initial migration from localStorage.
    Adds any assets that aren't already tracked.
    """
    added = []
    
    for asset_data in assets:
        # Check if already tracked
        result = await db.execute(
            select(TrackedAsset).filter(
                TrackedAsset.user_id == current_user.id,
                TrackedAsset.symbol == asset_data.symbol.upper()
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            continue
        
        # Parse asset type
        try:
            asset_type = AssetType[asset_data.asset_type.upper()]
        except KeyError:
            asset_type = AssetType.STOCK
        
        # Create tracked asset
        tracked = TrackedAsset(
            user_id=current_user.id,
            symbol=asset_data.symbol.upper(),
            name=asset_data.name,
            asset_type=asset_type,
            exchange=asset_data.exchange
        )
        
        db.add(tracked)
        added.append(tracked)
    
    if added:
        await db.commit()
        for t in added:
            await db.refresh(t)
    
    # Return all tracked assets
    result = await db.execute(
        select(TrackedAsset)
        .filter(TrackedAsset.user_id == current_user.id)
        .order_by(TrackedAsset.tracked_at.desc())
    )
    all_tracked = result.scalars().all()
    
    return [
        TrackedAssetResponse(
            id=str(t.id),
            symbol=t.symbol,
            name=t.name,
            asset_type=t.asset_type.value if hasattr(t.asset_type, 'value') else str(t.asset_type),
            exchange=t.exchange,
            tracked_at=t.tracked_at
        )
        for t in all_tracked
    ]

