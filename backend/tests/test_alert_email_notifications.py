"""Tests for alert email notifications via SendGrid."""
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.config import settings
from app.models.alert import (
    AlertRule,
    ConditionType,
    NotificationChannel,
    RepeatBehavior,
)
from app.models.asset import Asset
from app.models.user import User
from app.services.email_templates import build_alert_email_html
from app.services.notifications import notification_service
from app.workers import alerts as alerts_worker


def test_build_alert_email_html_includes_symbol_and_price():
    html = build_alert_email_html(
        symbol="AAPL",
        asset_name="Apple Inc.",
        message="Price alert fired.",
        condition_text="above $200",
        price="205.50",
        triggered_at="2026-05-21 12:00",
    )
    assert "AAPL" in html
    assert "Apple Inc." in html
    assert "above $200" in html
    assert "205.50" in html
    assert "MarketEye Alert" in html


@pytest.mark.asyncio
async def test_send_alert_email_passes_html_to_send_email(monkeypatch):
    captured = {}

    async def fake_send_email(to, subject, body, html=None):
        captured.update(
            {"to": to, "subject": subject, "body": body, "html": html}
        )
        return {"status": "sent", "provider": "sendgrid"}

    monkeypatch.setattr(notification_service, "send_email", fake_send_email)

    result = await notification_service.send_alert_email(
        to="user@example.com",
        subject="MarketEye Alert: BTC",
        body="BTC is above $100000",
        symbol="BTC",
        asset_name="Bitcoin",
        condition_text="above $100000",
        price="101000",
        triggered_at="2026-05-21 12:00",
    )

    assert result["status"] == "sent"
    assert captured["to"] == "user@example.com"
    assert captured["html"] is not None
    assert "BTC" in captured["html"]


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
    user = SimpleNamespace(id=uuid4(), email="alice@example.com", phone_number=None)
    asset = SimpleNamespace(
        symbol="ETH",
        name="Ethereum",
        current_price=Decimal("3500"),
    )
    alert = SimpleNamespace(notification_channel=NotificationChannel.EMAIL)

    with patch.object(
        alerts_worker,
        "_send_email_notification",
        new_callable=AsyncMock,
        return_value={"status": "sent", "provider": "sendgrid"},
    ) as mock_email:
        result = await alerts_worker._dispatch_alert_notifications(
            alert, user, asset, "ETH alert"
        )

    mock_email.assert_awaited_once()
    assert result["status"] == "sent"
    assert result["provider"] == "sendgrid"


@pytest.mark.asyncio
async def test_dispatch_multi_channel_sends_email_and_push():
    user = SimpleNamespace(
        id=uuid4(),
        email="alice@example.com",
        phone_number="+15551234567",
    )
    asset = SimpleNamespace(
        symbol="ETH",
        name="Ethereum",
        current_price=Decimal("3500"),
    )
    alert = SimpleNamespace(notification_channel=NotificationChannel.MULTI)

    with (
        patch.object(
            alerts_worker,
            "_send_email_notification",
            new_callable=AsyncMock,
            return_value={"status": "sent", "provider": "sendgrid"},
        ) as mock_email,
        patch.object(
            alerts_worker,
            "_send_push_notification",
            new_callable=AsyncMock,
            return_value={"status": "sent", "provider": "sse_push"},
        ) as mock_push,
    ):
        result = await alerts_worker._dispatch_alert_notifications(
            alert, user, asset, "ETH alert"
        )

    mock_email.assert_awaited_once()
    mock_push.assert_awaited_once()
    assert result["status"] == "sent"
    assert "email" in result["channels"]
    assert "push" in result["channels"]
