"""
Public endpoints (no authentication required).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.base import AsyncSessionLocal
from app.models.asset import Asset
from app.services.market_data import market_data_service
from typing import List, Dict, Any
import asyncio

router = APIRouter()


async def get_db() -> AsyncSession:
    """Get database session without auth."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@router.get("/trending")
async def get_trending_assets() -> Dict[str, Any]:
    """
    Get trending assets for landing page (no auth required).
    Returns popular stocks and crypto with live data.
    """
    trending_symbols = {
        "stocks": ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA", "META"],
        "crypto": ["BTC", "ETH", "SOL", "BNB", "ADA", "XRP"]
    }

    results = {
        "stocks": [],
        "crypto": [],
        "market_summary": {
            "total_assets": 12,
            "avg_change_24h": 0,
            "gainers": 0,
            "losers": 0
        }
    }

    total_change = 0
    count = 0

    # Fetch stock data
    for symbol in trending_symbols["stocks"]:
        try:
            data = await market_data_service.get_stock_price(symbol)
            if data:
                results["stocks"].append(data)
                if data.get("change_percent_24h"):
                    change = float(data["change_percent_24h"])
                    total_change += change
                    count += 1
                    if change > 0:
                        results["market_summary"]["gainers"] += 1
                    else:
                        results["market_summary"]["losers"] += 1
        except Exception as e:
            continue

    # Fetch crypto data
    for symbol in trending_symbols["crypto"]:
        try:
            data = await market_data_service.get_crypto_price(symbol)
            if data:
                results["crypto"].append(data)
                if data.get("change_percent_24h"):
                    change = float(data["change_percent_24h"])
                    total_change += change
                    count += 1
                    if change > 0:
                        results["market_summary"]["gainers"] += 1
                    else:
                        results["market_summary"]["losers"] += 1
        except Exception as e:
            continue

    if count > 0:
        results["market_summary"]["avg_change_24h"] = round(total_change / count, 2)

    return results


@router.get("/market-stats")
async def get_market_stats() -> Dict[str, Any]:
    """
    Get overall market statistics for landing page.
    """
    return {
        "total_users": "10,000+",
        "alerts_triggered_today": "25,847",
        "assets_monitored": "15,000+",
        "uptime": "99.9%",
        "avg_response_time": "< 100ms"
    }
