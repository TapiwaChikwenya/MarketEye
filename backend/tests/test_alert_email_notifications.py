"""Tests for production alert email templates and dispatch."""
from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.models.alert import ConditionType, NotificationChannel, RepeatBehavior
from app.models.asset import AssetType
from app.services.email_templates import (
    AlertEmailContext,
    build_alert_email_context,
    build_alert_email_html,
    build_alert_email_plain,
    build_demo_alert_email_context,
)
from app.services.notifications import notification_service
from app.workers import alerts as alerts_worker


def _sample_user(name="Jordan Trader", email="jordan@example.com", time_zone="America/Chicago"):
    return SimpleNamespace(
        id=uuid4(),
        name=name,
        email=email,
        phone_number=None,
        time_zone=time_zone,
    )


def _sample_asset():
    return SimpleNamespace(
        symbol="AAPL",
        name="Apple Inc.",
        asset_type=AssetType.STOCK,
        exchange="NASDAQ",
        current_price=Decimal("198.50"),
        change_24h=Decimal("3.25"),
        change_percent_24h=Decimal("1.67"),
    )


def _sample_alert():
    return SimpleNamespace(
        name="AAPL above 195",
        condition_type=ConditionType.PRICE_ABOVE,
        threshold_value=Decimal("195"),
        repeat_behavior=RepeatBehavior.ONCE_PER_DAY,
    )


def test_build_alert_email_context_personalizes_recipient_name():
    ctx = build_alert_email_context(
        user=_sample_user(name="Tapiwa"),
        asset=_sample_asset(),
        alert=_sample_alert(),
        frontend_base_url="http://localhost:5173",
    )
    assert ctx.recipient_name == "Tapiwa"
    assert "AAPL" in ctx.email_subject
    assert "AAPL" in ctx.condition_headline
    assert ctx.threshold_value == "$195"
    assert ctx.current_price == "$198.50"
    assert ctx.change_percent_24h == "+1.67%"


def test_build_alert_email_context_falls_back_to_email_local_part():
    ctx = build_alert_email_context(
        user=_sample_user(name=None, email="tapiwachikwenya@gmail.com"),
        asset=_sample_asset(),
        alert=_sample_alert(),
        frontend_base_url="http://localhost:5173",
    )
    assert ctx.recipient_name == "Tapiwachikwenya"


def test_build_alert_email_html_includes_trader_fields():
    ctx = build_alert_email_context(
        user=_sample_user(),
        asset=_sample_asset(),
        alert=_sample_alert(),
        frontend_base_url="http://localhost:5173",
    )
    html = build_alert_email_html(ctx)
    plain = build_alert_email_plain(ctx)

    assert "Hi Jordan Trader" in html
    assert "AAPL" in html
    assert "Apple Inc." in html
    assert "NASDAQ" in html
    assert "Market snapshot" in html
    assert "Your rule" in html
    assert "Open dashboard" in html
    assert "http://localhost:5173/dashboard" in html
    assert "AAPL above 195" in html
    assert "Hi Jordan Trader" in plain
    assert "Triggered:" in plain


def test_build_alert_email_percent_change_condition():
    asset = _sample_asset()
    asset.change_percent_24h = Decimal("-5.2")
    alert = SimpleNamespace(
        name="BTC drop",
        condition_type=ConditionType.PERCENT_CHANGE_DOWN,
        threshold_value=Decimal("5"),
        repeat_behavior=RepeatBehavior.UNLIMITED,
    )
    ctx = build_alert_email_context(
        user=_sample_user(),
        asset=asset,
        alert=alert,
        frontend_base_url="https://app.example.com",
    )
    assert "24h decline" in ctx.condition_headline
    assert "-5.20%" in ctx.change_percent_24h


@pytest.mark.asyncio
async def test_send_alert_email_passes_html_to_send_email(monkeypatch):
    captured = {}

    async def fake_send_email(to, subject, body, html=None):
        captured.update({"to": to, "subject": subject, "body": body, "html": html})
        return {"status": "sent", "provider": "sendgrid"}

    monkeypatch.setattr(notification_service, "send_email", fake_send_email)

    ctx = build_alert_email_context(
        user=_sample_user(),
        asset=_sample_asset(),
        alert=_sample_alert(),
        frontend_base_url="http://localhost:5173",
    )
    result = await notification_service.send_alert_email(to="user@example.com", ctx=ctx)

    assert result["status"] == "sent"
    assert captured["to"] == "user@example.com"
    assert "AAPL alert" in captured["subject"]
    assert "Hi Jordan Trader" in captured["body"]
    assert captured["html"] is not None
    assert "AAPL" in captured["html"]


def test_repeat_behavior_blocks_once_per_hour():
    alert = SimpleNamespace(
        last_triggered_at=datetime.utcnow() - timedelta(minutes=30),
        repeat_behavior=RepeatBehavior.ONCE_PER_HOUR,
    )
    assert alerts_worker._repeat_behavior_blocks_retrigger(alert) is True

    alert.last_triggered_at = datetime.utcnow() - timedelta(hours=2)
    assert alerts_worker._repeat_behavior_blocks_retrigger(alert) is False


@pytest.mark.asyncio
async def test_dispatch_email_channel_calls_send_alert_email():
    user = _sample_user()
    asset = _sample_asset()
    alert = SimpleNamespace(notification_channel=NotificationChannel.EMAIL)

    with patch.object(
        alerts_worker,
        "_send_email_notification",
        new_callable=AsyncMock,
        return_value={"status": "sent", "provider": "sendgrid"},
    ) as mock_email:
        result = await alerts_worker._dispatch_alert_notifications(
            alert, user, asset, "fallback"
        )

    mock_email.assert_awaited_once()
    assert result["status"] == "sent"


def test_demo_alert_context_for_test_endpoint():
    ctx = build_demo_alert_email_context(
        _sample_user(name="Tapiwa"),
        "http://localhost:5173",
    )
    assert ctx.recipient_name == "Tapiwa"
    assert "test" in ctx.email_subject.lower()
