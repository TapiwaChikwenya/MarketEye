"""
Celery tasks for market data updates and historical data backfill.
"""
import asyncio
import logging
import time
from datetime import date, datetime, timedelta, UTC

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.celery_app import celery_app
from app.db.base import AsyncSessionLocal
from app.models.asset import Asset, AssetType
from app.models.price_history import PriceHistory
from app.models.tracked_asset import TrackedAsset
from app.services.market_data import (
    market_data_service,
    _fetch_yahoo_chart_sync,
    _fetch_coingecko_history_sync,
    STOCK_TICKER_DB,
    CRYPTO_SYMBOL_MAP,
)
from app.services.price_history_utils import safe_decimal, points_to_rows

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.market_data.update_all_asset_prices")
def update_all_asset_prices():
    """Update prices for all assets in the database."""
    asyncio.run(_update_all_asset_prices())


async def _update_all_asset_prices():
    """Fetch prices concurrently via asyncio.gather, then write to DB in one commit."""
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(select(Asset))
            assets = result.scalars().all()

            async def _fetch(asset: Asset):
                try:
                    return asset, await market_data_service.get_asset_price(
                        asset.symbol, asset.asset_type
                    )
                except Exception as e:
                    logger.error(f"Error updating price for {asset.symbol}: {e}")
                    return asset, None

            fetch_results = await asyncio.gather(
                *(_fetch(a) for a in assets), return_exceptions=True
            )

            updated_count = 0
            for entry in fetch_results:
                if isinstance(entry, BaseException):
                    continue
                asset, price_data = entry
                if price_data:
                    asset.current_price = price_data.get("current_price")
                    asset.market_cap = price_data.get("market_cap")
                    asset.volume_24h = price_data.get("volume_24h")
                    asset.change_24h = price_data.get("change_24h")
                    asset.change_percent_24h = price_data.get("change_percent_24h")
                    asset.last_updated = datetime.now(UTC)
                    updated_count += 1

            await session.commit()
            logger.info(f"Updated prices for {updated_count}/{len(assets)} assets")

        except Exception as e:
            logger.error(f"Error in update_all_asset_prices: {e}")
            await session.rollback()


@celery_app.task(name="app.workers.market_data.update_asset_price")
def update_asset_price(asset_id: str):
    """Update price for a specific asset."""
    import asyncio
    asyncio.run(_update_asset_price(asset_id))


async def _update_asset_price(asset_id: str):
    """Async implementation of update_asset_price."""
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(select(Asset).filter(Asset.id == asset_id))
            asset = result.scalar_one_or_none()

            if not asset:
                logger.warning(f"Asset {asset_id} not found")
                return

            price_data = await market_data_service.get_asset_price(
                asset.symbol,
                asset.asset_type
            )

            if price_data:
                asset.current_price = price_data.get("current_price")
                asset.market_cap = price_data.get("market_cap")
                asset.volume_24h = price_data.get("volume_24h")
                asset.change_24h = price_data.get("change_24h")
                asset.change_percent_24h = price_data.get("change_percent_24h")
                asset.last_updated = datetime.now(UTC)

                await session.commit()
                logger.info(f"Updated price for {asset.symbol}")

        except Exception as e:
            logger.error(f"Error updating asset {asset_id}: {e}")
            await session.rollback()


# ---------------------------------------------------------------------------
# Historical data backfill
# ---------------------------------------------------------------------------

async def _upsert_price_rows(rows: list[dict]) -> int:
    """Bulk upsert rows into price_history. Returns count of rows written."""
    if not rows:
        return 0
    async with AsyncSessionLocal() as session:
        stmt = pg_insert(PriceHistory).values(rows)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_symbol_date",
            set_={
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "volume": stmt.excluded.volume,
            },
        )
        await session.execute(stmt)
        await session.commit()
        return len(rows)


async def _gather_symbols() -> list[tuple[str, AssetType]]:
    """Collect all symbols worth backfilling: static DB + DB assets + tracked."""
    symbols: dict[str, AssetType] = {}

    for stock in STOCK_TICKER_DB:
        symbols[stock["symbol"].upper()] = AssetType.STOCK

    for sym in CRYPTO_SYMBOL_MAP:
        symbols[sym.upper()] = AssetType.CRYPTO

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Asset.symbol, Asset.asset_type))
        for sym, at in result.all():
            symbols[sym.upper()] = at

        result = await session.execute(
            select(TrackedAsset.symbol, TrackedAsset.asset_type)
        )
        for sym, at in result.all():
            symbols[sym.upper()] = at

    return list(symbols.items())


def _fetch_daily_points(
    symbol: str, asset_type: AssetType, period: str
) -> list[dict] | None:
    """Fetch daily OHLCV points for a symbol, using the appropriate API."""
    if asset_type == AssetType.CRYPTO:
        points = _fetch_coingecko_history_sync(symbol, period, "1d")
        if points:
            return points
        return _fetch_yahoo_chart_sync(f"{symbol}-USD", period, "1d")
    return _fetch_yahoo_chart_sync(symbol, period, "1d")


# ---------------------------------------------------------------------------
# Celery tasks: daily backfill and initial load
# ---------------------------------------------------------------------------

@celery_app.task(name="app.workers.market_data.backfill_daily_prices")
def backfill_daily_prices():
    """Backfill the last 5 trading days for all tracked symbols."""
    asyncio.run(_backfill_daily_prices())


async def _backfill_daily_prices():
    symbols = await _gather_symbols()
    total_rows = 0
    errors = 0

    for symbol, asset_type in symbols:
        try:
            points = await asyncio.to_thread(
                _fetch_daily_points, symbol, asset_type, "5d"
            )
            if points:
                rows = points_to_rows(symbol, asset_type, points)
                total_rows += await _upsert_price_rows(rows)
            time.sleep(0.5)
        except Exception as e:
            errors += 1
            logger.error("Backfill failed for %s: %s", symbol, e)

    logger.info(
        "Daily backfill complete: %d rows upserted for %d symbols (%d errors)",
        total_rows, len(symbols), errors,
    )


@celery_app.task(name="app.workers.market_data.initial_backfill")
def initial_backfill():
    """One-time load of 1 year of daily OHLCV for all known symbols."""
    asyncio.run(_initial_backfill())


async def _initial_backfill():
    symbols = await _gather_symbols()
    total_rows = 0
    errors = 0

    logger.info("Starting initial backfill for %d symbols", len(symbols))

    for i, (symbol, asset_type) in enumerate(symbols, 1):
        try:
            points = await asyncio.to_thread(
                _fetch_daily_points, symbol, asset_type, "1y"
            )
            if points:
                rows = points_to_rows(symbol, asset_type, points)
                count = await _upsert_price_rows(rows)
                total_rows += count
                logger.info(
                    "[%d/%d] %s: %d rows", i, len(symbols), symbol, count
                )
            else:
                logger.warning("[%d/%d] %s: no data returned", i, len(symbols), symbol)
            time.sleep(0.5)
        except Exception as e:
            errors += 1
            logger.error("[%d/%d] %s failed: %s", i, len(symbols), symbol, e)

    logger.info(
        "Initial backfill complete: %d rows for %d symbols (%d errors)",
        total_rows, len(symbols), errors,
    )
