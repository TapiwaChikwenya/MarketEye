"""Pure rules for alert delivery. No database."""
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal

from app.api.v1.alerts import _coerce_asset_type, _IMPLEMENTED_CONDITIONS
from app.models.alert import ConditionType
from app.models.asset import AssetType
from app.workers.alerts import clock_in_zone, in_quiet_hours, portfolio_level_met


def test_overnight_quiet_hours_cover_both_sides_of_midnight():
    start = time(22, 0)
    end = time(8, 0)
    assert in_quiet_hours(start, end, time(23, 30)) is True
    assert in_quiet_hours(start, end, time(7, 15)) is True
    assert in_quiet_hours(start, end, time(12, 0)) is False
    assert in_quiet_hours(start, end, time(22, 0)) is True
    assert in_quiet_hours(start, end, time(8, 0)) is True


def test_same_day_quiet_hours_do_not_wrap():
    start = time(9, 0)
    end = time(17, 0)
    assert in_quiet_hours(start, end, time(12, 0)) is True
    assert in_quiet_hours(start, end, time(8, 59)) is False
    assert in_quiet_hours(start, end, time(18, 0)) is False


def test_zero_length_quiet_window_does_not_suppress():
    assert in_quiet_hours(time(1, 0), time(1, 0), time(1, 0)) is False
    assert in_quiet_hours(None, time(8, 0), time(1, 0)) is False


def test_price_and_portfolio_levels_are_accepted():
    assert ConditionType.PRICE_ABOVE in _IMPLEMENTED_CONDITIONS
    assert ConditionType.PERCENT_CHANGE_DOWN in _IMPLEMENTED_CONDITIONS
    assert ConditionType.PORTFOLIO_VALUE_UP in _IMPLEMENTED_CONDITIONS
    assert ConditionType.PORTFOLIO_VALUE_DOWN in _IMPLEMENTED_CONDITIONS
    assert ConditionType.VOLUME_ABOVE not in _IMPLEMENTED_CONDITIONS
    assert ConditionType.MARKET_CAP_ABOVE not in _IMPLEMENTED_CONDITIONS


def test_quiet_hours_follow_the_user_zone():
    # 13:30 UTC is 22:30 in Tokyo and 08:30 in New York (standard time).
    now = datetime(2026, 11, 26, 13, 30, tzinfo=timezone.utc)
    tokyo = clock_in_zone("Asia/Tokyo", now)
    assert tokyo == time(22, 30)
    assert in_quiet_hours(time(22, 0), time(23, 0), tokyo) is True
    assert in_quiet_hours(time(22, 0), time(23, 0), now.timetz().replace(tzinfo=None)) is False
    assert clock_in_zone("Not/AZone", now) == time(13, 30)


def test_portfolio_level_needs_a_fresh_priced_book():
    now = datetime(2026, 11, 26, 15, 0)
    fresh = now - timedelta(minutes=5)
    stale = now - timedelta(hours=2)
    assert portfolio_level_met(
        current_value=Decimal("12000"),
        priced_holdings=2,
        calculated_at=fresh,
        now=now,
        condition=ConditionType.PORTFOLIO_VALUE_UP,
        threshold=Decimal("10000"),
    ) is True
    assert portfolio_level_met(
        current_value=Decimal("8000"),
        priced_holdings=2,
        calculated_at=fresh,
        now=now,
        condition=ConditionType.PORTFOLIO_VALUE_DOWN,
        threshold=Decimal("9000"),
    ) is True
    assert portfolio_level_met(
        current_value=Decimal("0"),
        priced_holdings=0,
        calculated_at=fresh,
        now=now,
        condition=ConditionType.PORTFOLIO_VALUE_DOWN,
        threshold=Decimal("9000"),
    ) is False
    assert portfolio_level_met(
        current_value=Decimal("8000"),
        priced_holdings=2,
        calculated_at=stale,
        now=now,
        condition=ConditionType.PORTFOLIO_VALUE_DOWN,
        threshold=Decimal("9000"),
    ) is False


def test_asset_type_coercion_accepts_ui_labels():
    assert _coerce_asset_type("STOCK") is AssetType.STOCK
    assert _coerce_asset_type("mutual fund") is AssetType.MUTUAL_FUND
    assert _coerce_asset_type(None) is AssetType.STOCK
    assert _coerce_asset_type("not-a-type") is AssetType.STOCK
