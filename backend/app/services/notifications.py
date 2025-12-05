"""
Notification service for SMS, calls, and email.
"""
import logging
from typing import Optional
from twilio.rest import Client
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

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
        html: Optional[str] = None
    ) -> dict:
        """
        Send email notification via SMTP.

        Args:
            to: Email address to send to
            subject: Email subject
            body: Plain text body
            html: Optional HTML body

        Returns:
            Dict with status
        """
        if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            # Demo mode - simulate email sending
            logger.info(f"[DEMO MODE] Email to {to}: {subject}")
            return {
                "status": "sent",
                "provider": "smtp_demo"
            }

        try:
            message = MIMEMultipart("alternative")
            message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
            message["To"] = to
            message["Subject"] = subject

            # Add plain text part
            text_part = MIMEText(body, "plain")
            message.attach(text_part)

            # Add HTML part if provided
            if html:
                html_part = MIMEText(html, "html")
                message.attach(html_part)

            # Send email
            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                start_tls=True,
            )

            return {
                "status": "sent",
                "provider": "smtp"
            }
        except Exception as e:
            logger.error(f"Failed to send email to {to}: {e}")
            return {
                "status": "error",
                "message": str(e),
                "provider": "smtp"
            }

    async def send_notification(
        self,
        channel: str,
        to: str,
        message: str,
        subject: Optional[str] = None
    ) -> dict:
        """
        Send notification via specified channel.

        Args:
            channel: Notification channel (SMS, CALL, EMAIL)
            to: Recipient (phone number or email)
            message: Message content
            subject: Email subject (for EMAIL channel)

        Returns:
            Dict with status
        """
        if channel == "SMS":
            return await self.send_sms(to, message)
        elif channel == "CALL":
            return await self.make_call(to, message)
        elif channel == "EMAIL":
            return await self.send_email(to, subject or "MarketEye Alert", message)
        else:
            return {"status": "error", "message": f"Unknown channel: {channel}"}


# Global instance
notification_service = NotificationService()
