"""
Celery tasks for alert evaluation and notifications.
"""
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from app.celery_app import celery_app
from app.db.base import AsyncSessionLocal
from app.models.alert import AlertRule, ConditionType
from app.models.asset import Asset
from app.models.user import User
from app.models.notification import NotificationLog, EventType, NotificationStatus
from app.services.notifications import notification_service
from sqlalchemy import select, delete

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.alerts.evaluate_all_alerts")
def evaluate_all_alerts():
    """Evaluate all active alert rules."""
    import asyncio
    asyncio.run(_evaluate_all_alerts())


async def _evaluate_all_alerts():
    """Async implementation of evaluate_all_alerts."""
    async with AsyncSessionLocal() as session:
        try:
            # Get all active alerts
            result = await session.execute(
                select(AlertRule)
                .filter(AlertRule.is_active == True)
            )
            alerts = result.scalars().all()

            triggered_count = 0
            for alert in alerts:
                try:
                    if await _should_trigger_alert(alert, session):
                        await _trigger_alert(alert, session)
                        triggered_count += 1
                except Exception as e:
                    logger.error(f"Error evaluating alert {alert.id}: {e}")
                    continue

            await session.commit()
            logger.info(f"Evaluated {len(alerts)} alerts, triggered {triggered_count}")

        except Exception as e:
            logger.error(f"Error in evaluate_all_alerts: {e}")
            await session.rollback()


async def _should_trigger_alert(alert: AlertRule, session) -> bool:
    """Determine if an alert should be triggered."""
    # Get asset
    if not alert.asset_id:
        return False

    result = await session.execute(select(Asset).filter(Asset.id == alert.asset_id))
    asset = result.scalar_one_or_none()

    if not asset or not asset.current_price:
        return False

    current_price = Decimal(asset.current_price)
    threshold = alert.threshold_value

    # Evaluate condition
    if alert.condition_type == ConditionType.PRICE_ABOVE:
        return current_price >= threshold
    elif alert.condition_type == ConditionType.PRICE_BELOW:
        return current_price <= threshold
    elif alert.condition_type == ConditionType.PERCENT_CHANGE_UP:
        if asset.change_percent_24h:
            change = Decimal(asset.change_percent_24h)
            return change >= threshold
    elif alert.condition_type == ConditionType.PERCENT_CHANGE_DOWN:
        if asset.change_percent_24h:
            change = Decimal(asset.change_percent_24h)
            return change <= -threshold

    return False


async def _trigger_alert(alert: AlertRule, session):
    """Trigger an alert and send notification."""
    from app.services.sse import publish_alert_sync

    result_obj = await session.execute(select(User).filter(User.id == alert.user_id))
    user = result_obj.scalar_one_or_none()

    result_obj = await session.execute(select(Asset).filter(Asset.id == alert.asset_id))
    asset = result_obj.scalar_one_or_none()

    if not user or not asset:
        return

    if user.quiet_hours_enabled and not alert.override_quiet_hours:
        current_time = datetime.utcnow().time()
        if user.quiet_hours_start and user.quiet_hours_end:
            if user.quiet_hours_start <= current_time <= user.quiet_hours_end:
                logger.info(f"Alert {alert.id} suppressed due to quiet hours")
                return

    message = alert.custom_message or _build_alert_message(alert, asset)

    condition_text = {
        ConditionType.PRICE_ABOVE: f"above ${alert.threshold_value}",
        ConditionType.PRICE_BELOW: f"below ${alert.threshold_value}",
        ConditionType.PERCENT_CHANGE_UP: f"up {alert.threshold_value}%",
        ConditionType.PERCENT_CHANGE_DOWN: f"down {alert.threshold_value}%",
    }.get(alert.condition_type, "condition met")

    send_result: dict | None = None

    if alert.notification_channel == "PUSH":
        payload = {
            "user_id": str(user.id),
            "type": "price_alert",
            "title": f"MarketEye Alert: {asset.symbol}",
            "body": message,
            "symbol": asset.symbol,
            "price": str(asset.current_price),
            "condition": f"is {condition_text}",
            "timestamp": datetime.utcnow().isoformat(),
        }
        try:
            publish_alert_sync(payload)
            send_result = {"status": "sent", "provider": "sse_push"}
            logger.info(f"Published PUSH alert to SSE for user {user.id}")
        except Exception as e:
            send_result = {"status": "failed", "error": str(e)}
            logger.error(f"Failed to publish PUSH alert: {e}")
    else:
        recipient = None
        if alert.notification_channel in ["SMS", "CALL"]:
            recipient = user.phone_number
        elif alert.notification_channel == "EMAIL":
            recipient = user.email

        if not recipient:
            logger.warning(f"No recipient configured for alert {alert.id}")
            return

        send_result = await notification_service.send_notification(
            channel=alert.notification_channel,
            to=recipient,
            message=message,
            subject=f"MarketEye Alert: {asset.symbol}",
        )

    log_entry = NotificationLog(
        user_id=user.id,
        alert_id=alert.id,
        asset_id=asset.id,
        event_type=EventType.ALERT_TRIGGERED,
        status=NotificationStatus.SENT if send_result.get("status") == "sent" else NotificationStatus.FAILED,
        message=message,
        details=send_result,
        provider=send_result.get("provider"),
        provider_message_id=send_result.get("message_id") or send_result.get("call_id"),
    )
    session.add(log_entry)

    alert.last_triggered_at = datetime.utcnow()
    alert.trigger_count += 1

    if alert.repeat_behavior == "one_time":
        alert.is_active = False

    logger.info(f"Triggered alert {alert.id} for {asset.symbol}")


def _build_alert_message(alert: AlertRule, asset: Asset) -> str:
    """Build default alert message."""
    condition_text = {
        ConditionType.PRICE_ABOVE: f"above ${alert.threshold_value}",
        ConditionType.PRICE_BELOW: f"below ${alert.threshold_value}",
        ConditionType.PERCENT_CHANGE_UP: f"up {alert.threshold_value}%",
        ConditionType.PERCENT_CHANGE_DOWN: f"down {alert.threshold_value}%",
    }.get(alert.condition_type, "condition met")

    return (
        f"MarketEye Alert: {asset.symbol} ({asset.name}) "
        f"is {condition_text}. "
        f"Current price: ${asset.current_price}"
    )


@celery_app.task(name="app.workers.alerts.cleanup_old_notifications")
def cleanup_old_notifications():
    """Clean up notification logs older than 30 days."""
    import asyncio
    asyncio.run(_cleanup_old_notifications())


async def _cleanup_old_notifications():
    """Async implementation of cleanup_old_notifications."""
    async with AsyncSessionLocal() as session:
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=30)

            await session.execute(
                delete(NotificationLog).where(NotificationLog.created_at < cutoff_date)
            )

            await session.commit()
            logger.info("Cleaned up old notification logs")

        except Exception as e:
            logger.error(f"Error cleaning up notifications: {e}")
            await session.rollback()
