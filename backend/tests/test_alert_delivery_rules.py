"""Pure rules for alert delivery. No database."""
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

from app.api.v1.alerts import _coerce_asset_type, _IMPLEMENTED_CONDITIONS
from app.models.alert import ConditionType
from app.models.asset import AssetType
from app.workers.alerts import (
    QUOTE_MAX_AGE,
    in_quiet_hours,
    price_alert_should_fire,
    quote_is_fresh,
)


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


def test_only_price_conditions_are_accepted():
    assert ConditionType.PRICE_ABOVE in _IMPLEMENTED_CONDITIONS
    assert ConditionType.PERCENT_CHANGE_DOWN in _IMPLEMENTED_CONDITIONS
    assert ConditionType.VOLUME_ABOVE not in _IMPLEMENTED_CONDITIONS
    assert ConditionType.PORTFOLIO_VALUE_UP not in _IMPLEMENTED_CONDITIONS


def _asset(price="100", change="1.5", age=timedelta(minutes=1), updated=True):
    now = datetime(2026, 11, 27, 15, 0, tzinfo=timezone.utc)
    return now, SimpleNamespace(
        symbol="AAPL",
        current_price=price,
        change_percent_24h=change,
        last_updated=(now - age) if updated else None,
    )


def test_fresh_price_above_fires():
    now, asset = _asset(price="150")
    alert = SimpleNamespace(
        condition_type=ConditionType.PRICE_ABOVE,
        threshold_value=Decimal("149"),
    )
    assert price_alert_should_fire(alert, asset, now=now) is True


def test_stale_quote_does_not_fire_even_when_the_level_is_crossed():
    now, asset = _asset(price="150", age=QUOTE_MAX_AGE + timedelta(seconds=1))
    alert = SimpleNamespace(
        condition_type=ConditionType.PRICE_ABOVE,
        threshold_value=Decimal("1"),
    )
    assert quote_is_fresh(asset.last_updated, now=now) is False
    assert price_alert_should_fire(alert, asset, now=now) is False


def test_missing_quote_timestamp_does_not_fire():
    now, asset = _asset(updated=False)
    alert = SimpleNamespace(
        condition_type=ConditionType.PRICE_BELOW,
        threshold_value=Decimal("1000"),
    )
    assert price_alert_should_fire(alert, asset, now=now) is False


def test_naive_utc_timestamp_is_fresh():
    now = datetime(2026, 11, 27, 15, 0, tzinfo=timezone.utc)
    stamp = datetime(2026, 11, 27, 14, 50)  # utcnow()-style, no tz
    assert quote_is_fresh(stamp, now=now) is True


def test_percent_down_uses_a_fresh_change():
    now, asset = _asset(change="-4.2")
    alert = SimpleNamespace(
        condition_type=ConditionType.PERCENT_CHANGE_DOWN,
        threshold_value=Decimal("3"),
    )
    assert price_alert_should_fire(alert, asset, now=now) is True


def test_asset_type_coercion_accepts_ui_labels():
    assert _coerce_asset_type("STOCK") is AssetType.STOCK
    assert _coerce_asset_type("mutual fund") is AssetType.MUTUAL_FUND
    assert _coerce_asset_type(None) is AssetType.STOCK
    assert _coerce_asset_type("not-a-type") is AssetType.STOCK
