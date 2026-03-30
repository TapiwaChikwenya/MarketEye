"""
Public endpoints (no authentication required).
"""
import time
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.base import AsyncSessionLocal
from app.models.asset import Asset, AssetType
from app.services.market_data import market_data_service
from typing import List, Dict, Any, Tuple
import asyncio

router = APIRouter()

_trending_cache: Dict[str, Any] = {}
_trending_cache_ts: float = 0.0
_TRENDING_CACHE_TTL = 300  # 5 minutes


async def get_db() -> AsyncSession:
    """Get database session without auth."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# ------------------------------------------------------------------
# Helpers for concurrent trending fetch
# ------------------------------------------------------------------

async def _fetch_stock(symbol: str) -> Tuple[str, Dict[str, Any] | None]:
    try:
        data = await market_data_service.get_stock_price(symbol)
        if data:
            data["asset_type"] = "STOCK"
        return ("stock", data)
    except Exception:
        return ("stock", None)


async def _fetch_crypto(symbol: str) -> Tuple[str, Dict[str, Any] | None]:
    try:
        data = await market_data_service.get_crypto_price(symbol)
        if data:
            data["asset_type"] = "CRYPTO"
        return ("crypto", data)
    except Exception:
        return ("crypto", None)


async def _fetch_fund(symbol: str) -> Tuple[str, Dict[str, Any] | None]:
    try:
        if len(symbol) == 5 and symbol.endswith("X"):
            data = await market_data_service.get_mutual_fund_price(symbol)
            if data:
                data["asset_type"] = "MUTUAL_FUND"
        else:
            data = await market_data_service.get_stock_price(symbol)
            if data:
                data["asset_type"] = "ETF"
        return ("fund", data)
    except Exception:
        return ("fund", None)


@router.get("/trending")
async def get_trending_assets() -> Dict[str, Any]:
    """
    Get trending assets for landing page (no auth required).
    Cached for 5 minutes to avoid hammering upstream providers.
    """
    global _trending_cache, _trending_cache_ts

    if _trending_cache and (time.time() - _trending_cache_ts) < _TRENDING_CACHE_TTL:
        return _trending_cache

    result = await _fetch_trending_data()
    if result.get("stocks") or result.get("crypto"):
        _trending_cache = result
        _trending_cache_ts = time.time()
    return result


async def _fetch_trending_data() -> Dict[str, Any]:
    """Fetch fresh trending data from all providers."""
    trending_symbols = {
        "stocks": ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA", "META", "AMZN", "JPM", "V", "MA"],
        "crypto": ["BTC", "ETH", "SOL", "BNB", "ADA", "XRP", "DOGE", "AVAX", "MATIC"],
        "funds": [
            "FXAIX", "FSKAX", "FZROX", "FZILX", "FXNAX", "FTBFX",
            "FBALX", "FCNTX", "FDGRX", "FBGRX", "FSPSX", "FSIVX",
            "FSAGX", "FSCSX",
            "VOO", "VTI", "SPY", "QQQ", "IVV",
        ],
    }

    results: Dict[str, Any] = {
        "stocks": [],
        "crypto": [],
        "funds": [],
        "market_summary": {
            "total_assets": 18,
            "avg_change_24h": 0,
            "gainers": 0,
            "losers": 0,
        },
    }

    tasks = []
    tasks.extend(_fetch_stock(s) for s in trending_symbols["stocks"])
    tasks.extend(_fetch_crypto(s) for s in trending_symbols["crypto"])
    tasks.extend(_fetch_fund(s) for s in trending_symbols["funds"])

    all_results = await asyncio.gather(*tasks, return_exceptions=True)

    total_change = 0.0
    count = 0

    bucket_map = {"stock": "stocks", "crypto": "crypto", "fund": "funds"}

    for entry in all_results:
        if isinstance(entry, BaseException):
            continue
        category, data = entry
        if data is None:
            continue

        bucket = bucket_map.get(category)
        if bucket:
            results[bucket].append(data)

        raw_pct = data.get("change_percent_24h")
        if raw_pct is not None:
            try:
                change = float(raw_pct)
            except (ValueError, TypeError):
                continue
            total_change += change
            count += 1
            if change > 0:
                results["market_summary"]["gainers"] += 1
            else:
                results["market_summary"]["losers"] += 1

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

    fund_results, asset_results = await asyncio.gather(
        market_data_service.search_funds(q),
        market_data_service.search_assets(q),
    )

    merged: list = fund_results + asset_results
    seen: set = set()
    deduped: list = []
    for item in merged:
        sym = item.get("symbol", "").upper()
        if sym not in seen:
            seen.add(sym)
            deduped.append(item)

    q_upper = q.strip().upper()
    _TOKENIZED = {"xstock", "tokenized", "wrapped", "dinari", "ondo", "rstock"}

    def _sort_key(item: dict) -> tuple:
        sym = item.get("symbol", "").upper()
        name_lower = (item.get("name") or "").lower()
        atype = item.get("asset_type", "")
        exact = 0 if sym == q_upper else 1
        junk = 1 if any(t in name_lower for t in _TOKENIZED) else 0
        rank = {"STOCK": 0, "ETF": 1, "MUTUAL_FUND": 2, "CRYPTO": 3}.get(atype, 4)
        return (exact, junk, rank)

    deduped.sort(key=_sort_key)
    return {"results": deduped[:30]}


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
