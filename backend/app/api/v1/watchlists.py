"""
Watchlist endpoints.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.core.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.watchlist import Watchlist, WatchlistAsset
from app.models.asset import Asset
from app.schemas.watchlist import (
    WatchlistCreate,
    WatchlistUpdate,
    WatchlistResponse,
    WatchlistWithAssets,
    AddAssetToWatchlist,
)

router = APIRouter()


@router.get("/", response_model=List[WatchlistResponse])
async def get_watchlists(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all watchlists for current user."""
    result = await db.execute(
        select(Watchlist)
        .filter(Watchlist.user_id == current_user.id)
        .order_by(Watchlist.sort_order)
    )
    watchlists = result.scalars().all()
    return watchlists


@router.post("/", response_model=WatchlistResponse, status_code=201)
async def create_watchlist(
    watchlist_data: WatchlistCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new watchlist."""
    watchlist = Watchlist(
        **watchlist_data.dict(),
        user_id=current_user.id
    )
    db.add(watchlist)
    await db.commit()
    await db.refresh(watchlist)
    return watchlist


@router.get("/{watchlist_id}", response_model=WatchlistWithAssets)
async def get_watchlist(
    watchlist_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific watchlist with its assets."""
    result = await db.execute(
        select(Watchlist).filter(
            Watchlist.id == watchlist_id,
            Watchlist.user_id == current_user.id
        )
    )
    watchlist = result.scalar_one_or_none()

    if not watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    # Get associated assets
    result = await db.execute(
        select(WatchlistAsset)
        .filter(WatchlistAsset.watchlist_id == watchlist_id)
        .order_by(WatchlistAsset.sort_order)
    )
    watchlist_assets = result.scalars().all()

    return {
        **watchlist.__dict__,
        "asset_ids": [wa.asset_id for wa in watchlist_assets]
    }


@router.put("/{watchlist_id}", response_model=WatchlistResponse)
async def update_watchlist(
    watchlist_id: str,
    watchlist_update: WatchlistUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a watchlist."""
    result = await db.execute(
        select(Watchlist).filter(
            Watchlist.id == watchlist_id,
            Watchlist.user_id == current_user.id
        )
    )
    watchlist = result.scalar_one_or_none()

    if not watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    # Update fields
    for field, value in watchlist_update.dict(exclude_unset=True).items():
        setattr(watchlist, field, value)

    await db.commit()
    await db.refresh(watchlist)
    return watchlist


@router.delete("/{watchlist_id}", status_code=204)
async def delete_watchlist(
    watchlist_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a watchlist."""
    result = await db.execute(
        select(Watchlist).filter(
            Watchlist.id == watchlist_id,
            Watchlist.user_id == current_user.id
        )
    )
    watchlist = result.scalar_one_or_none()

    if not watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    await db.delete(watchlist)
    await db.commit()


@router.post("/{watchlist_id}/assets", status_code=201)
async def add_asset_to_watchlist(
    watchlist_id: str,
    asset_data: AddAssetToWatchlist,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Add an asset to a watchlist."""
    # Verify watchlist ownership
    result = await db.execute(
        select(Watchlist).filter(
            Watchlist.id == watchlist_id,
            Watchlist.user_id == current_user.id
        )
    )
    watchlist = result.scalar_one_or_none()

    if not watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    # Verify asset exists
    result = await db.execute(select(Asset).filter(Asset.id == asset_data.asset_id))
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Check if already added
    result = await db.execute(
        select(WatchlistAsset).filter(
            WatchlistAsset.watchlist_id == watchlist_id,
            WatchlistAsset.asset_id == asset_data.asset_id
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=400, detail="Asset already in watchlist")

    # Add asset to watchlist
    watchlist_asset = WatchlistAsset(
        watchlist_id=watchlist_id,
        asset_id=asset_data.asset_id,
        sort_order=asset_data.sort_order
    )
    db.add(watchlist_asset)
    await db.commit()

    return {"message": "Asset added to watchlist"}


@router.delete("/{watchlist_id}/assets/{asset_id}", status_code=204)
async def remove_asset_from_watchlist(
    watchlist_id: str,
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Remove an asset from a watchlist."""
    # Verify watchlist ownership
    result = await db.execute(
        select(Watchlist).filter(
            Watchlist.id == watchlist_id,
            Watchlist.user_id == current_user.id
        )
    )
    watchlist = result.scalar_one_or_none()

    if not watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    # Delete the association
    await db.execute(
        delete(WatchlistAsset).where(
            WatchlistAsset.watchlist_id == watchlist_id,
            WatchlistAsset.asset_id == asset_id
        )
    )
    await db.commit()
