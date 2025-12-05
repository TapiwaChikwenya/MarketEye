"""
Celery tasks for market data updates.
"""
import logging
from app.celery_app import celery_app
from app.db.base import AsyncSessionLocal
from app.models.asset import Asset
from app.services.market_data import market_data_service
from sqlalchemy import select
from datetime import datetime

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.market_data.update_all_asset_prices")
def update_all_asset_prices():
    """Update prices for all assets in the database."""
    import asyncio
    asyncio.run(_update_all_asset_prices())


async def _update_all_asset_prices():
    """Async implementation of update_all_asset_prices."""
    async with AsyncSessionLocal() as session:
        try:
            # Get all assets
            result = await session.execute(select(Asset))
            assets = result.scalars().all()

            updated_count = 0
            for asset in assets:
                try:
                    # Fetch latest price
                    price_data = await market_data_service.get_asset_price(
                        asset.symbol,
                        asset.asset_type
                    )

                    if price_data:
                        # Update asset with new data
                        asset.current_price = price_data.get('current_price')
                        asset.market_cap = price_data.get('market_cap')
                        asset.volume_24h = price_data.get('volume_24h')
                        asset.change_24h = price_data.get('change_24h')
                        asset.change_percent_24h = price_data.get('change_percent_24h')
                        asset.last_updated = datetime.utcnow()
                        updated_count += 1

                except Exception as e:
                    logger.error(f"Error updating price for {asset.symbol}: {e}")
                    continue

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
                asset.current_price = price_data.get('current_price')
                asset.market_cap = price_data.get('market_cap')
                asset.volume_24h = price_data.get('volume_24h')
                asset.change_24h = price_data.get('change_24h')
                asset.change_percent_24h = price_data.get('change_percent_24h')
                asset.last_updated = datetime.utcnow()

                await session.commit()
                logger.info(f"Updated price for {asset.symbol}")

        except Exception as e:
            logger.error(f"Error updating asset {asset_id}: {e}")
            await session.rollback()
