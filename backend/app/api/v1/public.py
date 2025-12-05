"""
Public endpoints (no authentication required).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.base import AsyncSessionLocal
from app.models.asset import Asset, AssetType
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
    Returns popular stocks, crypto, and funds with live data.
    """
    trending_symbols = {
        "stocks": ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA", "META", "AMZN", "JPM", "V", "MA"],
        "crypto": ["BTC", "ETH", "SOL", "BNB", "ADA", "XRP", "DOGE", "AVAX", "MATIC"],
        "funds": [
            # Fidelity / mutual funds
            "FXAIX", "FSKAX", "FZROX", "FZILX", "FXNAX", "FTBFX",
            "FBALX", "FCNTX", "FDGRX", "FBGRX", "FSPSX", "FSIVX",
            "FSAGX", "FSCSX",
            # Popular ETFs
            "VOO", "VTI", "SPY", "QQQ", "IVV"
        ]
    }

    results = {
        "stocks": [],
        "crypto": [],
        "funds": [],
        "market_summary": {
            "total_assets": 18,
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
                data['asset_type'] = 'STOCK'
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
                data['asset_type'] = 'CRYPTO'
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

    # Fetch fund data (mutual funds and ETFs)
    for symbol in trending_symbols["funds"]:
        try:
            # Check if it's a mutual fund (typically 5 letters ending in X) or ETF
            if len(symbol) == 5 and symbol.endswith('X'):
                data = await market_data_service.get_mutual_fund_price(symbol)
                if data:
                    data['asset_type'] = 'MUTUAL_FUND'
            else:
                data = await market_data_service.get_stock_price(symbol)
                if data:
                    data['asset_type'] = 'ETF'
            
            if data:
                results["funds"].append(data)
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


@router.get("/history")
async def get_public_history(
    symbol: str,
    asset_type: AssetType,
    period: str = "1mo",
    interval: str = "1d",
) -> Dict[str, Any]:
    """
    Public historical data endpoint by symbol/asset_type (no auth required).
    Returns real market data; does not fall back to mock values.
    """
    data = await market_data_service.get_historical_data(
        symbol=symbol,
        asset_type=asset_type,
        period=period,
        interval=interval,
    )
    if not data:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="No historical data available")
    return {"data": data}


@router.get("/search")
async def search_assets(q: str) -> Dict[str, Any]:
    """
    Search for assets across all types (stocks, crypto, funds).
    No auth required.
    """
    if not q or len(q) < 1:
        return {"results": []}
    
    results = []
    
    # Search funds first (Fidelity, Vanguard, ETFs)
    fund_results = await market_data_service.search_funds(q)
    results.extend(fund_results)
    
    # Search stocks
    stock_results = await market_data_service.search_assets(q)
    for r in stock_results:
        if not any(existing['symbol'] == r['symbol'] for existing in results):
            results.append(r)
    
    return {"results": results[:30]}


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


@router.get("/asset/{symbol}/history")
async def get_asset_history_public(
    symbol: str,
    asset_type: str = "STOCK",
    period: str = "1mo",
    interval: str = "1d"
) -> Dict[str, Any]:
    """
    Get historical price data for an asset (public, no auth required).
    Useful for displaying charts on the dashboard.
    """
    from app.models.asset import AssetType
    
    try:
        # Determine asset type
        if asset_type.upper() == "CRYPTO":
            at = AssetType.CRYPTO
        else:
            at = AssetType.STOCK
        
        # Fetch historical data
        historical_data = await market_data_service.get_historical_data(
            symbol,
            at,
            period=period,
            interval=interval
        )
        
        if not historical_data:
            return {
                "symbol": symbol,
                "period": period,
                "interval": interval,
                "data": []
            }
        
        return {
            "symbol": symbol,
            "period": period,
            "interval": interval,
            "data": historical_data
        }
    except Exception as e:
        return {
            "symbol": symbol,
            "period": period,
            "interval": interval,
            "data": [],
            "error": str(e)
        }


@router.get("/asset/{symbol}/price")
async def get_asset_price_public(
    symbol: str,
    asset_type: str = "STOCK"
) -> Dict[str, Any]:
    """
    Get current price for an asset (public, no auth required).
    """
    try:
        if asset_type.upper() == "CRYPTO":
            data = await market_data_service.get_crypto_price(symbol)
        else:
            data = await market_data_service.get_stock_price(symbol)
        
        if not data:
            return {"error": "Unable to fetch price data", "symbol": symbol}
        
        return data
    except Exception as e:
        return {"error": str(e), "symbol": symbol}
