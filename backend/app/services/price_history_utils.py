"""
Shared utilities for price history processing.

Kept separate from workers/market_data.py to avoid Celery import dependency
in tests and the service layer.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.models.asset import AssetType


def safe_decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def points_to_rows(
    symbol: str, asset_type: AssetType, points: list[dict]
) -> list[dict]:
    """Convert API response points into dicts ready for PriceHistory upsert."""
    rows: list[dict] = []
    seen_dates: set[date] = set()
    for pt in points:
        try:
            ts = pt["timestamp"]
            if "T" in ts:
                dt = datetime.fromisoformat(ts)
            else:
                dt = datetime.strptime(ts, "%Y-%m-%d")
            d = dt.date()
        except (KeyError, ValueError):
            continue

        if d in seen_dates:
            continue
        seen_dates.add(d)

        rows.append({
            "symbol": symbol.upper(),
            "asset_type": asset_type.value,
            "date": d,
            "open": safe_decimal(pt["open"]),
            "high": safe_decimal(pt["high"]),
            "low": safe_decimal(pt["low"]),
            "close": safe_decimal(pt["close"]),
            "volume": safe_decimal(pt.get("volume", 0)),
        })
    return rows
