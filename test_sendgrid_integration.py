"""
Tests for the SendGrid integration in notification_service.send_email().

These tests mock SendGridAPIClient so they run offline and never touch
the real API. They verify:
  1. With no API key, send_email() falls back to demo mode.
  2. With an API key, the SDK is called with the correct Mail payload.
  3. A 202 response is reported as status="sent".
  4. A 4xx response is reported as status="error" with the status code.
  5. An exception inside the SDK call is caught (never propagated).
"""
import asyncio
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import pytest

from app.services.notifications import notification_service
from app.core.config import settings


# ---------- Helpers ---------------------------------------------------

def _fake_response(status_code: int, message_id: str = "abc123") -> SimpleNamespace:
    """Build a stand-in for the SendGrid Response object."""
    return SimpleNamespace(
        status_code=status_code,
        headers={"X-Message-Id": message_id},
        body=b"",
    )


# ---------- Tests -----------------------------------------------------

def test_send_email_demo_mode_when_no_api_key(monkeypatch):
    """No API key configured -> demo mode, no SDK call attempted."""
    monkeypatch.setattr(settings, "SENDGRID_API_KEY", None)

    result = asyncio.run(notification_service.send_email(
        to="alice@example.com",
        subject="Hello",
        body="Plain text body",
    ))

    assert result["status"] == "sent"
    assert result["provider"] == "sendgrid_demo"


def test_send_email_calls_sendgrid_with_correct_payload(monkeypatch):
    """With an API key, the SDK is called with from/to/subject/html."""
    monkeypatch.setattr(settings, "SENDGRID_API_KEY", "SG." + "x" * 40)
    monkeypatch.setattr(settings, "SENDGRID_FROM_EMAIL", "noreply@example.com")
    monkeypatch.setattr(settings, "SENDGRID_FROM_NAME", "MarketEye")

    fake_client = MagicMock()
    fake_client.send.return_value = _fake_response(202)

    # Patch the lazy-imported class inside the sendgrid module.
    with patch("sendgrid.SendGridAPIClient", return_value=fake_client) as ctor:
        result = asyncio.run(notification_service.send_email(
            to="alice@example.com",
            subject="Reset your password",
            body="Plain body",
            html="<p>HTML body</p>",
        ))

    # Constructor received the API key.
    ctor.assert_called_once()
    assert ctor.call_args.args[0].startswith("SG.")

    # client.send() was invoked exactly once with a Mail object.
    fake_client.send.assert_called_once()
    mail_obj = fake_client.send.call_args.args[0]
    # The Mail object should carry our subject and recipient. We poke at
    # its serialized form so we don't depend on private attributes.
    payload = mail_obj.get()
    assert payload["subject"] == "Reset your password"
    assert payload["from"]["email"] == "noreply@example.com"
    assert payload["from"]["name"] == "MarketEye"
    assert payload["personalizations"][0]["to"][0]["email"] == "alice@example.com"
    # Both plain and html parts are attached.
    mime_types = {c["type"] for c in payload["content"]}
    assert "text/plain" in mime_types
    assert "text/html" in mime_types

    # Result reports success.
    assert result["status"] == "sent"
    assert result["provider"] == "sendgrid"
    assert result["status_code"] == 202


def test_send_email_reports_sendgrid_error_codes(monkeypatch):
    """4xx response -> status='error', code surfaced for callers."""
    monkeypatch.setattr(settings, "SENDGRID_API_KEY", "SG." + "x" * 40)

    fake_client = MagicMock()
    fake_client.send.return_value = _fake_response(403)  # sender mismatch

    with patch("sendgrid.SendGridAPIClient", return_value=fake_client):
        result = asyncio.run(notification_service.send_email(
            to="alice@example.com",
            subject="X",
            body="Y",
        ))

    assert result["status"] == "error"
    assert result["provider"] == "sendgrid"
    assert result["status_code"] == 403


def test_send_email_swallows_sdk_exceptions(monkeypatch):
    """Network or SDK errors must NOT propagate - caller gets a dict."""
    monkeypatch.setattr(settings, "SENDGRID_API_KEY", "SG." + "x" * 40)

    fake_client = MagicMock()
    fake_client.send.side_effect = RuntimeError("connection refused")

    with patch("sendgrid.SendGridAPIClient", return_value=fake_client):
        result = asyncio.run(notification_service.send_email(
            to="alice@example.com",
            subject="X",
            body="Y",
        ))

    assert result["status"] == "error"
    assert "connection refused" in result["message"]
