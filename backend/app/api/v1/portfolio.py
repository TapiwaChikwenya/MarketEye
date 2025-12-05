"""
Portfolio endpoints.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.portfolio import Portfolio, PortfolioHolding
from app.schemas.portfolio import (
    PortfolioCreate,
    PortfolioResponse,
    PortfolioWithHoldings,
    PortfolioHoldingCreate,
    PortfolioHoldingResponse,
)

router = APIRouter()


@router.get("/", response_model=PortfolioWithHoldings)
async def get_portfolio(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get user's portfolio with holdings."""
    result = await db.execute(
        select(Portfolio).filter(Portfolio.user_id == current_user.id)
    )
    portfolio = result.scalar_one_or_none()

    if not portfolio:
        # Create default portfolio if doesn't exist
        portfolio = Portfolio(user_id=current_user.id)
        db.add(portfolio)
        await db.commit()
        await db.refresh(portfolio)

    # Get holdings
    result = await db.execute(
        select(PortfolioHolding).filter(PortfolioHolding.portfolio_id == portfolio.id)
    )
    holdings = result.scalars().all()

    return {
        **portfolio.__dict__,
        "holdings": holdings
    }


@router.post("/holdings", response_model=PortfolioHoldingResponse, status_code=201)
async def add_holding(
    holding_data: PortfolioHoldingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Add a holding to the portfolio."""
    # Get or create portfolio
    result = await db.execute(
        select(Portfolio).filter(Portfolio.user_id == current_user.id)
    )
    portfolio = result.scalar_one_or_none()

    if not portfolio:
        portfolio = Portfolio(user_id=current_user.id)
        db.add(portfolio)
        await db.flush()

    # Calculate total cost basis
    total_cost_basis = float(holding_data.quantity * holding_data.average_cost_basis)

    # Create holding
    holding = PortfolioHolding(
        portfolio_id=portfolio.id,
        asset_id=holding_data.asset_id,
        quantity=holding_data.quantity,
        average_cost_basis=holding_data.average_cost_basis,
        total_cost_basis=total_cost_basis,
        purchase_date=holding_data.purchase_date,
    )

    db.add(holding)
    await db.commit()
    await db.refresh(holding)

    return holding


@router.delete("/holdings/{holding_id}", status_code=204)
async def remove_holding(
    holding_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Remove a holding from the portfolio."""
    # Get portfolio
    result = await db.execute(
        select(Portfolio).filter(Portfolio.user_id == current_user.id)
    )
    portfolio = result.scalar_one_or_none()

    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # Get holding
    result = await db.execute(
        select(PortfolioHolding).filter(
            PortfolioHolding.id == holding_id,
            PortfolioHolding.portfolio_id == portfolio.id
        )
    )
    holding = result.scalar_one_or_none()

    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")

    await db.delete(holding)
    await db.commit()
