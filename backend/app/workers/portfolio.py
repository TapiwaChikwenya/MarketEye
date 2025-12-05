"""
Celery tasks for portfolio calculations.
"""
import logging
from decimal import Decimal
from datetime import datetime
from app.celery_app import celery_app
from app.db.base import AsyncSessionLocal
from app.models.portfolio import Portfolio, PortfolioHolding
from app.models.asset import Asset
from sqlalchemy import select

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.portfolio.update_all_portfolios")
def update_all_portfolios():
    """Update calculations for all portfolios."""
    import asyncio
    asyncio.run(_update_all_portfolios())


async def _update_all_portfolios():
    """Async implementation of update_all_portfolios."""
    async with AsyncSessionLocal() as session:
        try:
            # Get all portfolios
            result = await session.execute(select(Portfolio))
            portfolios = result.scalars().all()

            updated_count = 0
            for portfolio in portfolios:
                try:
                    await _calculate_portfolio_values(portfolio, session)
                    updated_count += 1
                except Exception as e:
                    logger.error(f"Error updating portfolio {portfolio.id}: {e}")
                    continue

            await session.commit()
            logger.info(f"Updated {updated_count}/{len(portfolios)} portfolios")

        except Exception as e:
            logger.error(f"Error in update_all_portfolios: {e}")
            await session.rollback()


async def _calculate_portfolio_values(portfolio: Portfolio, session):
    """Calculate portfolio values and P&L."""
    # Get all holdings
    result = await session.execute(
        select(PortfolioHolding).filter(PortfolioHolding.portfolio_id == portfolio.id)
    )
    holdings = result.scalars().all()

    total_cost_basis = Decimal(0)
    total_current_value = Decimal(0)

    for holding in holdings:
        # Get asset with current price
        result = await session.execute(select(Asset).filter(Asset.id == holding.asset_id))
        asset = result.scalar_one_or_none()

        if not asset or not asset.current_price:
            continue

        # Update holding values
        current_price = Decimal(asset.current_price)
        quantity = holding.quantity

        holding.current_price = current_price
        holding.current_value = current_price * quantity
        holding.unrealized_pnl = holding.current_value - holding.total_cost_basis

        if holding.total_cost_basis > 0:
            holding.unrealized_pnl_percent = (
                (holding.unrealized_pnl / holding.total_cost_basis) * 100
            )

        total_cost_basis += holding.total_cost_basis
        total_current_value += holding.current_value

    # Update portfolio totals
    portfolio.total_cost_basis = total_cost_basis
    portfolio.current_value = total_current_value
    portfolio.unrealized_pnl = total_current_value - total_cost_basis

    if total_cost_basis > 0:
        portfolio.unrealized_pnl_percent = (
            (portfolio.unrealized_pnl / total_cost_basis) * 100
        )

    portfolio.last_calculated_at = datetime.utcnow()


@celery_app.task(name="app.workers.portfolio.calculate_portfolio")
def calculate_portfolio(portfolio_id: str):
    """Calculate values for a specific portfolio."""
    import asyncio
    asyncio.run(_calculate_portfolio(portfolio_id))


async def _calculate_portfolio(portfolio_id: str):
    """Async implementation of calculate_portfolio."""
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(select(Portfolio).filter(Portfolio.id == portfolio_id))
            portfolio = result.scalar_one_or_none()

            if not portfolio:
                logger.warning(f"Portfolio {portfolio_id} not found")
                return

            await _calculate_portfolio_values(portfolio, session)
            await session.commit()

            logger.info(f"Updated portfolio {portfolio_id}")

        except Exception as e:
            logger.error(f"Error calculating portfolio {portfolio_id}: {e}")
            await session.rollback()
