"""
Celery tasks for alert evaluation and notifications.
"""
import logging
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from sqlalchemy import select, delete, func

from app.celery_app import celery_app
from app.core.config import settings
from app.db.base import AsyncSessionLocal
from app.models.alert import AlertRule, ConditionType, NotificationChannel, RepeatBehavior
from app.models.asset import Asset
from app.models.user import User
from app.models.notification import NotificationLog, EventType, NotificationStatus
from app.services.email_templates import build_alert_email_context
from app.services.notifications import notification_service

logger = logging.getLogger(__name__)


def in_quiet_hours(start, end, current) -> bool:
    """Whether ``current`` falls inside a quiet window.

    Same-day windows use start <= now <= end. Overnight windows (22:00–08:00,
    the settings default) wrap past midnight: now >= start or now <= end.
    A zero-length window (start == end) does not suppress alerts.
    """
    if start is None or end is None or start == end:
        return False
    if start < end:
        return start <= current <= end
    return current >= start or current <= end


def _parse_decimal(raw: object) -> Decimal | None:
    if raw is None:
        return None
    text = str(raw).strip().replace(",", "").replace("$", "")
    if not text or text.lower() in {"none", "null", "nan", "n/a", "-"}:
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def condition_is_met(
    condition: ConditionType,
    *,
    price: Decimal | None,
    change_percent: Decimal | None,
    volume: Decimal | None,
    market_cap: Decimal | None,
    threshold: Decimal,
) -> bool:
    """Price and percent use the last quote. Volume and market cap use the 24h figures already stored on the asset.

    Portfolio conditions are still not evaluated: there is no single portfolio
    mark the worker can compare without walking every holding.
    """
    if condition == ConditionType.PRICE_ABOVE:
        return price is not None and price >= threshold
    if condition == ConditionType.PRICE_BELOW:
        return price is not None and price <= threshold
    if condition == ConditionType.PERCENT_CHANGE_UP:
        return change_percent is not None and change_percent >= threshold
    if condition == ConditionType.PERCENT_CHANGE_DOWN:
        return change_percent is not None and change_percent <= -abs(threshold)
    if condition == ConditionType.VOLUME_ABOVE:
        return volume is not None and volume >= threshold
    if condition == ConditionType.MARKET_CAP_ABOVE:
        return market_cap is not None and market_cap >= threshold
    return False


def _condition_text(alert: AlertRule) -> str:
    return {
        ConditionType.PRICE_ABOVE: f"above ${alert.threshold_value}",
        ConditionType.PRICE_BELOW: f"below ${alert.threshold_value}",
        ConditionType.PERCENT_CHANGE_UP: f"up {alert.threshold_value}%",
        ConditionType.PERCENT_CHANGE_DOWN: f"down {alert.threshold_value}%",
        ConditionType.VOLUME_ABOVE: f"24h volume above {alert.threshold_value}",
        ConditionType.MARKET_CAP_ABOVE: f"market cap above {alert.threshold_value}",
    }.get(alert.condition_type, "condition met")


def _build_alert_message(alert: AlertRule, asset: Asset) -> str:
    """Build default alert message."""
    return (
        f"MarketEye Alert: {asset.symbol} ({asset.name}) "
        f"is {_condition_text(alert)}. "
        f"Current price: ${asset.current_price}"
    )


async def _user_over_daily_notification_limit(user_id, session) -> bool:
    """True when the user has hit MAX_NOTIFICATIONS_PER_DAY sent notifications."""
    cutoff = datetime.utcnow() - timedelta(days=1)
    result = await session.execute(
        select(func.count(NotificationLog.id)).where(
            NotificationLog.user_id == user_id,
            NotificationLog.status == NotificationStatus.SENT,
            NotificationLog.created_at >= cutoff,
        )
    )
    count = result.scalar() or 0
    return count >= settings.MAX_NOTIFICATIONS_PER_DAY


def _repeat_behavior_blocks_retrigger(alert: AlertRule) -> bool:
    """True when repeat_behavior suppresses another send since last_triggered_at."""
    if not alert.last_triggered_at:
        return False

    last = alert.last_triggered_at
    if last.tzinfo is not None:
        last = last.replace(tzinfo=None)

    elapsed = datetime.utcnow() - last
    if alert.repeat_behavior == RepeatBehavior.ONCE_PER_HOUR:
        return elapsed < timedelta(hours=1)
    if alert.repeat_behavior == RepeatBehavior.ONCE_PER_DAY:
        return elapsed < timedelta(days=1)
    return False


async def _send_push_notification(user: User, asset: Asset, alert: AlertRule, message: str) -> dict:
    from app.services.sse import publish_alert_sync

    condition_text = _condition_text(alert)
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
        logger.info(f"Published PUSH alert to SSE for user {user.id}")
        return {"status": "sent", "provider": "sse_push"}
    except Exception as e:
        logger.error(f"Failed to publish PUSH alert: {e}")
        return {"status": "failed", "error": str(e), "provider": "sse_push"}


async def _send_email_notification(
    user: User, asset: Asset, alert: AlertRule, message: str
) -> dict:
    ctx = build_alert_email_context(
        user=user,
        asset=asset,
        alert=alert,
        frontend_base_url=settings.FRONTEND_BASE_URL,
    )
    return await notification_service.send_alert_email(to=user.email, ctx=ctx)


async def _dispatch_alert_notifications(
    alert: AlertRule, user: User, asset: Asset, message: str
) -> dict:
    """
    Send notifications for the alert's channel(s).
    MULTI sends email plus in-app push.
    Returns a combined result dict for logging.
    """
    channel = alert.notification_channel
    results: dict[str, dict] = {}

    if channel in (NotificationChannel.EMAIL, NotificationChannel.MULTI):
        if not user.email:
            results["email"] = {
                "status": "error",
                "message": "User email not configured",
            }
        else:
            results["email"] = await _send_email_notification(
                user, asset, alert, message
            )

    if channel in (NotificationChannel.PUSH, NotificationChannel.MULTI):
        results["push"] = await _send_push_notification(
            user, asset, alert, message
        )

    if channel in (NotificationChannel.SMS, NotificationChannel.CALL):
        recipient = user.phone_number
        if not recipient:
            results[channel.value.lower()] = {
                "status": "error",
                "message": "Phone number not configured",
            }
        else:
            results[channel.value.lower()] = await notification_service.send_notification(
                channel=channel.value,
                to=recipient,
                message=message,
                subject=f"MarketEye Alert: {asset.symbol}",
            )

    if not results:
        return {"status": "error", "message": f"Unsupported channel: {channel}"}

    any_sent = any(r.get("status") == "sent" for r in results.values())
    primary = results.get("email") or results.get("push") or next(iter(results.values()))

    return {
        "status": "sent" if any_sent else primary.get("status", "error"),
        "provider": primary.get("provider"),
        "message_id": primary.get("message_id") or primary.get("call_id"),
        "channels": results,
    }


@celery_app.task(name="app.workers.alerts.evaluate_all_alerts")
def evaluate_all_alerts():
    """Evaluate all active alert rules."""
    import asyncio
    asyncio.run(_evaluate_all_alerts())


async def _evaluate_all_alerts():
    """Async implementation of evaluate_all_alerts."""
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(AlertRule).filter(AlertRule.is_active == True)
            )
            alerts = result.scalars().all()

            triggered_count = 0
            for alert in alerts:
                try:
                    if _repeat_behavior_blocks_retrigger(alert):
                        continue
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
    if not alert.asset_id:
        return False

    result = await session.execute(select(Asset).filter(Asset.id == alert.asset_id))
    asset = result.scalar_one_or_none()

    if not asset:
        return False

    return condition_is_met(
        alert.condition_type,
        price=_parse_decimal(asset.current_price),
        change_percent=_parse_decimal(asset.change_percent_24h),
        volume=_parse_decimal(asset.volume_24h),
        market_cap=_parse_decimal(asset.market_cap),
        threshold=Decimal(alert.threshold_value),
    )


async def _trigger_alert(alert: AlertRule, session):
    """Trigger an alert and send notification."""
    result_obj = await session.execute(select(User).filter(User.id == alert.user_id))
    user = result_obj.scalar_one_or_none()

    result_obj = await session.execute(select(Asset).filter(Asset.id == alert.asset_id))
    asset = result_obj.scalar_one_or_none()

    if not user or not asset:
        return

    if await _user_over_daily_notification_limit(user.id, session):
        logger.warning(
            "Skipping alert %s: user %s hit daily notification limit (%s)",
            alert.id,
            user.id,
            settings.MAX_NOTIFICATIONS_PER_DAY,
        )
        return

    if user.quiet_hours_enabled and not alert.override_quiet_hours:
        current_time = datetime.utcnow().time()
        if in_quiet_hours(user.quiet_hours_start, user.quiet_hours_end, current_time):
            logger.info(f"Alert {alert.id} suppressed due to quiet hours")
            return

    message = alert.custom_message or _build_alert_message(alert, asset)
    email_ctx = build_alert_email_context(
        user=user,
        asset=asset,
        alert=alert,
        frontend_base_url=settings.FRONTEND_BASE_URL,
    )
    subject = email_ctx.email_subject

    send_result = await _dispatch_alert_notifications(alert, user, asset, message)

    delivered = send_result.get("status") == "sent"
    if not delivered:
        logger.warning(
            "Alert %s notification issue for %s: %s",
            alert.id,
            asset.symbol,
            send_result,
        )

    log_entry = NotificationLog(
        user_id=user.id,
        alert_id=alert.id,
        asset_id=asset.id,
        event_type=EventType.ALERT_TRIGGERED,
        status=(
            NotificationStatus.SENT
            if delivered
            else NotificationStatus.FAILED
        ),
        subject=subject,
        message=message,
        details=send_result,
        provider=send_result.get("provider"),
        provider_message_id=send_result.get("message_id") or send_result.get("call_id"),
        sent_at=datetime.utcnow() if delivered else None,
    )
    session.add(log_entry)

    # A failed send must not consume a one-time alert. TradingView keeps a
    # once-only alert armed when a schedule blocks delivery; the same rule
    # applies when email or SMS does not actually go out.
    if delivered:
        alert.last_triggered_at = datetime.utcnow()
        alert.trigger_count += 1
        if alert.repeat_behavior == RepeatBehavior.ONE_TIME:
            alert.is_active = False
        logger.info(f"Triggered alert {alert.id} for {asset.symbol}")
    else:
        logger.info(f"Alert {alert.id} for {asset.symbol} stays active after a failed send")


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
