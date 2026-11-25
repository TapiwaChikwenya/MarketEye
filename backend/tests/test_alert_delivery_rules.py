"""Pure rules for alert delivery. No database."""
from datetime import time

from app.api.v1.alerts import _coerce_asset_type, _IMPLEMENTED_CONDITIONS
from app.models.alert import ConditionType
from app.models.asset import AssetType
from decimal import Decimal

from app.workers.alerts import condition_is_met, in_quiet_hours


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


def test_price_volume_and_market_cap_conditions_are_accepted():
    assert ConditionType.PRICE_ABOVE in _IMPLEMENTED_CONDITIONS
    assert ConditionType.PERCENT_CHANGE_DOWN in _IMPLEMENTED_CONDITIONS
    assert ConditionType.VOLUME_ABOVE in _IMPLEMENTED_CONDITIONS
    assert ConditionType.MARKET_CAP_ABOVE in _IMPLEMENTED_CONDITIONS
    assert ConditionType.PORTFOLIO_VALUE_UP not in _IMPLEMENTED_CONDITIONS
    assert ConditionType.PORTFOLIO_VALUE_DOWN not in _IMPLEMENTED_CONDITIONS


def test_volume_and_market_cap_use_stored_24h_figures():
    assert condition_is_met(
        ConditionType.VOLUME_ABOVE,
        price=None,
        change_percent=None,
        volume=Decimal("1500000"),
        market_cap=None,
        threshold=Decimal("1000000"),
    )
    assert not condition_is_met(
        ConditionType.VOLUME_ABOVE,
        price=Decimal("10"),
        change_percent=None,
        volume=Decimal("10"),
        market_cap=None,
        threshold=Decimal("1000000"),
    )
    assert condition_is_met(
        ConditionType.MARKET_CAP_ABOVE,
        price=Decimal("10"),
        change_percent=None,
        volume=None,
        market_cap=Decimal("2000000000"),
        threshold=Decimal("1500000000"),
    )
    assert not condition_is_met(
        ConditionType.VOLUME_ABOVE,
        price=Decimal("10"),
        change_percent=None,
        volume=None,
        market_cap=Decimal("999"),
        threshold=Decimal("1"),
    )
    assert not condition_is_met(
        ConditionType.PORTFOLIO_VALUE_UP,
        price=Decimal("10"),
        change_percent=Decimal("50"),
        volume=Decimal("999"),
        market_cap=Decimal("999"),
        threshold=Decimal("1"),
    )


def test_percent_down_compares_against_a_negative_move():
    assert condition_is_met(
        ConditionType.PERCENT_CHANGE_DOWN,
        price=Decimal("90"),
        change_percent=Decimal("-6"),
        volume=None,
        market_cap=None,
        threshold=Decimal("5"),
    )
    assert not condition_is_met(
        ConditionType.PERCENT_CHANGE_DOWN,
        price=Decimal("90"),
        change_percent=Decimal("-4"),
        volume=None,
        market_cap=None,
        threshold=Decimal("5"),
    )


def test_asset_type_coercion_accepts_ui_labels():
    assert _coerce_asset_type("STOCK") is AssetType.STOCK
    assert _coerce_asset_type("mutual fund") is AssetType.MUTUAL_FUND
    assert _coerce_asset_type(None) is AssetType.STOCK
    assert _coerce_asset_type("not-a-type") is AssetType.STOCK
