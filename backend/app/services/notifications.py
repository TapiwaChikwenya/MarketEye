"""
Notification service for SMS, calls, and email.
"""
import asyncio
import logging
from typing import Optional
from twilio.rest import Client
from app.core.config import settings
from app.services.email_templates import (
    AlertEmailContext,
    build_alert_email_html,
    build_alert_email_plain,
)

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending notifications via various channels."""

    def __init__(self):
        # Initialize Twilio client if credentials are available
        if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
            try:
                self.twilio_client = Client(
                    settings.TWILIO_ACCOUNT_SID,
                    settings.TWILIO_AUTH_TOKEN
                )
                logger.info("Twilio initialized successfully")
            except Exception as e:
                self.twilio_client = None
                logger.warning(f"Twilio initialization failed: {e}. SMS/Call notifications disabled.")
        else:
            self.twilio_client = None
            logger.info("Twilio credentials not configured. SMS/Call notifications will be simulated in demo mode.")

    async def send_sms(self, to: str, message: str) -> dict:
        """
        Send SMS notification via Twilio.

        Args:
            to: Phone number to send to
            message: Message content

        Returns:
            Dict with status and message_id or error
        """
        if not self.twilio_client:
            # Demo mode - simulate SMS sending
            logger.info(f"[DEMO MODE] SMS to {to}: {message}")
            return {
                "status": "sent",
                "message_id": f"demo_sms_{hash(message) % 100000}",
                "provider": "twilio_demo"
            }

        try:
            twilio_message = self.twilio_client.messages.create(
                body=message,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=to
            )

            return {
                "status": "sent",
                "message_id": twilio_message.sid,
                "provider": "twilio"
            }
        except Exception as e:
            logger.error(f"Failed to send SMS to {to}: {e}")
            return {
                "status": "error",
                "message": str(e),
                "provider": "twilio"
            }

    async def make_call(self, to: str, message: str) -> dict:
        """
        Make a voice call via Twilio with TTS.

        Args:
            to: Phone number to call
            message: Message to speak

        Returns:
            Dict with status and call_id or error
        """
        if not self.twilio_client:
            # Demo mode - simulate call
            logger.info(f"[DEMO MODE] Call to {to}: {message}")
            return {
                "status": "sent",
                "call_id": f"demo_call_{hash(message) % 100000}",
                "provider": "twilio_demo"
            }

        try:
            # Create TwiML for text-to-speech
            twiml = f'<Response><Say voice="Polly.Joanna">{message}</Say></Response>'

            call = self.twilio_client.calls.create(
                twiml=twiml,
                to=to,
                from_=settings.TWILIO_PHONE_NUMBER
            )

            return {
                "status": "sent",
                "call_id": call.sid,
                "provider": "twilio"
            }
        except Exception as e:
            logger.error(f"Failed to make call to {to}: {e}")
            return {
                "status": "error",
                "message": str(e),
                "provider": "twilio"
            }

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html: Optional[str] = None,
    ) -> dict:
        """
        Send a transactional email via SendGrid's v3 /mail/send HTTP API.

        Returns:
            dict with at least {"status": "sent"|"error", "provider": ...}.
            Never raises - failures are logged and surfaced in the return
            value so callers (alert workers, password reset) can decide
            how to handle them.
        """
        if not settings.SENDGRID_API_KEY:
            logger.info(f"[DEMO MODE] Email to {to}: {subject}")
            return {"status": "sent", "provider": "sendgrid_demo"}

        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import (
                Mail,
                MailSettings,
                SandBoxMode,
                TrackingSettings,
                ClickTracking,
                OpenTracking,
            )

            message = Mail(
                from_email=(settings.SENDGRID_FROM_EMAIL, settings.SENDGRID_FROM_NAME),
                to_emails=to,
                subject=subject,
                plain_text_content=body,
                html_content=html,
            )

            # Disable link/open tracking so auth URLs are not rewritten through
            # url####.yourdomain.com (broken SSL on tracking subdomains is common).
            message.tracking_settings = TrackingSettings(
                click_tracking=ClickTracking(enable=False, enable_text=False),
                open_tracking=OpenTracking(enable=False),
            )

            if settings.SENDGRID_SANDBOX_MODE:
                message.mail_settings = MailSettings(
                    sandbox_mode=SandBoxMode(enable=True)
                )

            client = SendGridAPIClient(settings.SENDGRID_API_KEY)
            response = await asyncio.to_thread(client.send, message)

            if 200 <= response.status_code < 300:
                return {
                    "status": "sent",
                    "provider": "sendgrid",
                    "message_id": response.headers.get("X-Message-Id"),
                    "status_code": response.status_code,
                }

            logger.error(
                "SendGrid returned %s for %s: %s",
                response.status_code,
                to,
                str(response.body)[:500],
            )
            return {
                "status": "error",
                "provider": "sendgrid",
                "message": f"SendGrid HTTP {response.status_code}",
                "status_code": response.status_code,
            }

        except Exception as e:
            logger.exception(f"SendGrid send failed for {to}: {e}")
            return {"status": "error", "provider": "sendgrid", "message": str(e)}

    async def send_alert_email(self, to: str, ctx: AlertEmailContext) -> dict:
        """Send a trader-focused HTML + plain-text alert email via SendGrid."""
        plain = build_alert_email_plain(ctx)
        html = build_alert_email_html(ctx)
        return await self.send_email(to, ctx.email_subject, plain, html=html)

    async def send_notification(
        self,
        channel: str,
        to: str,
        message: str,
        subject: Optional[str] = None,
        html: Optional[str] = None,
    ) -> dict:
        """
        Send notification via specified channel.

        Args:
            channel: Notification channel (SMS, CALL, EMAIL)
            to: Recipient (phone number or email)
            message: Message content
            subject: Email subject (for EMAIL channel)
            html: Optional HTML body (EMAIL channel only)

        Returns:
            Dict with status
        """
        if channel == "SMS":
            return await self.send_sms(to, message)
        elif channel == "CALL":
            return await self.make_call(to, message)
        elif channel == "EMAIL":
            return await self.send_email(
                to, subject or "MarketEye Alert", message, html=html
            )
        else:
            return {"status": "error", "message": f"Unknown channel: {channel}"}


# Global instance
notification_service = NotificationService()
