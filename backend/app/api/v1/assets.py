"""
Asset endpoints.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.core.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.asset import Asset, AssetType
from app.schemas.asset import AssetCreate, AssetResponse, AssetUpdate
from app.services.market_data import market_data_service
from datetime import datetime

router = APIRouter()


@router.get("/search", response_model=List[AssetResponse])
async def search_assets(
    q: str = Query(..., min_length=1, description="Search query"),
    asset_type: Optional[AssetType] = None,
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Search for assets."""
    # Search in database first
    query = select(Asset).where(
        or_(
            Asset.symbol.ilike(f"%{q}%"),
            Asset.name.ilike(f"%{q}%")
        )
    )

    if asset_type:
        query = query.where(Asset.asset_type == asset_type)

    query = query.limit(limit)
    result = await db.execute(query)
    assets = result.scalars().all()

    # If not found in DB, search external APIs
    if not assets:
        external_results = await market_data_service.search_assets(q, asset_type)

        # Create assets in database for found results
        for result_data in external_results[:limit]:
            asset = Asset(
                symbol=result_data['symbol'],
                name=result_data['name'],
                asset_type=AssetType[result_data['asset_type']],
                exchange=result_data.get('exchange'),
            )
            db.add(asset)

        await db.commit()

        # Re-query to get the created assets
        result = await db.execute(
            select(Asset).where(Asset.symbol.in_([r['symbol'] for r in external_results]))
        )
        assets = result.scalars().all()

    return assets


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get asset by ID."""
    result = await db.execute(select(Asset).filter(Asset.id == asset_id))
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    return asset


@router.get("/{asset_id}/price", response_model=dict)
async def get_asset_price(
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get current price for an asset."""
    result = await db.execute(select(Asset).filter(Asset.id == asset_id))
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Fetch latest price from market data service
    price_data = await market_data_service.get_asset_price(asset.symbol, asset.asset_type)

    if not price_data:
        raise HTTPException(status_code=503, detail="Unable to fetch price data")

    # Update asset cache
    asset.current_price = price_data.get('current_price')
    asset.market_cap = price_data.get('market_cap')
    asset.volume_24h = price_data.get('volume_24h')
    asset.change_24h = price_data.get('change_24h')
    asset.change_percent_24h = price_data.get('change_percent_24h')
    asset.last_updated = datetime.utcnow()

    await db.commit()

    return price_data


@router.get("/{asset_id}/history", response_model=dict)
async def get_asset_history(
    asset_id: str,
    period: str = Query("1mo", description="Period (1d, 5d, 1mo, 3mo, 6mo, 1y, etc.)"),
    interval: str = Query("1d", description="Interval (1m, 5m, 15m, 1h, 1d, etc.)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get historical price data for an asset."""
    result = await db.execute(select(Asset).filter(Asset.id == asset_id))
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Fetch historical data
    historical_data = await market_data_service.get_historical_data(
        asset.symbol,
        asset.asset_type,
        period=period,
        interval=interval
    )

    if not historical_data:
        raise HTTPException(status_code=503, detail="Unable to fetch historical data")

    return {
        "asset_id": str(asset.id),
        "symbol": asset.symbol,
        "period": period,
        "interval": interval,
        "data": historical_data
    }


@router.post("/", response_model=AssetResponse, status_code=201)
async def create_asset(
    asset_data: AssetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new asset (admin only or auto-created from search)."""
    # Check if asset already exists
    result = await db.execute(select(Asset).filter(Asset.symbol == asset_data.symbol))
    existing_asset = result.scalar_one_or_none()

    if existing_asset:
        raise HTTPException(status_code=400, detail="Asset already exists")

    # Create new asset
    asset = Asset(**asset_data.dict())
    db.add(asset)
    await db.commit()
    await db.refresh(asset)

    return asset
