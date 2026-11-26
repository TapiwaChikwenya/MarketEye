"""
Celery tasks for alert evaluation and notifications.
"""
import logging
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select, delete, func

from app.celery_app import celery_app
from app.core.config import settings
from app.db.base import AsyncSessionLocal
from app.models.alert import AlertRule, ConditionType, NotificationChannel, RepeatBehavior
from app.models.asset import Asset
from app.models.portfolio import Portfolio, PortfolioHolding
from app.models.user import User
from app.models.notification import NotificationLog, EventType, NotificationStatus
from app.services.email_templates import (
    build_alert_email_context,
    build_portfolio_alert_email_context,
)
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


_PORTFOLIO_CONDITIONS = {
    ConditionType.PORTFOLIO_VALUE_UP,
    ConditionType.PORTFOLIO_VALUE_DOWN,
}
_PORTFOLIO_MAX_AGE = timedelta(minutes=30)


def clock_in_zone(tz_name: str | None, now: datetime | None = None) -> time:
    """Wall-clock time in the user's zone. Invalid zones fall back to UTC.

    Quiet-hour settings are the hours the user picked next to their timezone.
    Comparing those hours to ``datetime.utcnow()`` keeps a Chicago 22:00–08:00
    window quiet in the middle of the local afternoon.
    """
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    name = (tz_name or "UTC").strip() or "UTC"
    try:
        local = moment.astimezone(ZoneInfo(name))
    except Exception:
        local = moment.astimezone(timezone.utc)
    return local.time().replace(tzinfo=None)


def portfolio_level_met(
    *,
    current_value,
    priced_holdings: int,
    calculated_at: datetime | None,
    now: datetime,
    condition: ConditionType,
    threshold,
) -> bool:
    """Dollar level on a book that has a recent price.

    An empty or unpriced portfolio is not "below" a level: quotes may simply
    be missing. A calculation older than 30 minutes is skipped so a stalled
    portfolio job cannot fire on a stale total.
    """
    if priced_holdings <= 0 or current_value is None or calculated_at is None:
        return False
    if condition not in _PORTFOLIO_CONDITIONS:
        return False
    last = calculated_at
    moment = now
    if last.tzinfo is not None:
        last = last.replace(tzinfo=None)
    if moment.tzinfo is not None:
        moment = moment.replace(tzinfo=None)
    if moment - last > _PORTFOLIO_MAX_AGE:
        return False
    value = Decimal(current_value)
    level = Decimal(threshold)
    if condition == ConditionType.PORTFOLIO_VALUE_UP:
        return value >= level
    return value <= level


def _condition_text(alert: AlertRule) -> str:
    return {
        ConditionType.PRICE_ABOVE: f"above ${alert.threshold_value}",
        ConditionType.PRICE_BELOW: f"below ${alert.threshold_value}",
        ConditionType.PERCENT_CHANGE_UP: f"up {alert.threshold_value}%",
        ConditionType.PERCENT_CHANGE_DOWN: f"down {alert.threshold_value}%",
        ConditionType.PORTFOLIO_VALUE_UP: f"above ${alert.threshold_value}",
        ConditionType.PORTFOLIO_VALUE_DOWN: f"below ${alert.threshold_value}",
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


async def _send_push_notification(
    user: User,
    asset: Asset | None,
    alert: AlertRule,
    message: str,
    portfolio_value=None,
) -> dict:
    from app.services.sse import publish_alert_sync

    condition_text = _condition_text(alert)
    symbol = asset.symbol if asset is not None else "PORTFOLIO"
    price = asset.current_price if asset is not None else portfolio_value
    payload = {
        "user_id": str(user.id),
        "type": "price_alert" if asset is not None else "portfolio_alert",
        "title": f"MarketEye Alert: {symbol}",
        "body": message,
        "symbol": symbol,
        "price": str(price),
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
    user: User,
    asset: Asset | None,
    alert: AlertRule,
    message: str,
    portfolio_value=None,
) -> dict:
    if alert.condition_type in _PORTFOLIO_CONDITIONS:
        ctx = build_portfolio_alert_email_context(
            user=user,
            alert=alert,
            current_value=portfolio_value,
            frontend_base_url=settings.FRONTEND_BASE_URL,
        )
    else:
        ctx = build_alert_email_context(
            user=user,
            asset=asset,
            alert=alert,
            frontend_base_url=settings.FRONTEND_BASE_URL,
        )
    return await notification_service.send_alert_email(to=user.email, ctx=ctx)


async def _dispatch_alert_notifications(
    alert: AlertRule,
    user: User,
    asset: Asset | None,
    message: str,
    portfolio_value=None,
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
                user, asset, alert, message, portfolio_value=portfolio_value
            )

    if channel in (NotificationChannel.PUSH, NotificationChannel.MULTI):
        results["push"] = await _send_push_notification(
            user, asset, alert, message, portfolio_value=portfolio_value
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
                subject=f"MarketEye Alert: {asset.symbol if asset is not None else 'PORTFOLIO'}",
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


async def _portfolio_snapshot(alert: AlertRule, session):
    """Return (portfolio, priced holding count) or None when the user has no book."""
    result = await session.execute(select(Portfolio).filter(Portfolio.user_id == alert.user_id))
    portfolio = result.scalar_one_or_none()
    if portfolio is None:
        return None
    holdings = (
        await session.execute(
            select(PortfolioHolding).filter(PortfolioHolding.portfolio_id == portfolio.id)
        )
    ).scalars().all()
    priced = sum(
        1
        for holding in holdings
        if holding.current_price is not None and holding.current_value is not None
    )
    return portfolio, priced


async def _should_trigger_alert(alert: AlertRule, session) -> bool:
    """Determine if an alert should be triggered."""
    if alert.condition_type in _PORTFOLIO_CONDITIONS:
        snap = await _portfolio_snapshot(alert, session)
        if snap is None:
            return False
        portfolio, priced = snap
        return portfolio_level_met(
            current_value=portfolio.current_value,
            priced_holdings=priced,
            calculated_at=portfolio.last_calculated_at,
            now=datetime.utcnow(),
            condition=alert.condition_type,
            threshold=alert.threshold_value,
        )

    if not alert.asset_id:
        return False

    result = await session.execute(select(Asset).filter(Asset.id == alert.asset_id))
    asset = result.scalar_one_or_none()

    if not asset or not asset.current_price:
        return False

    current_price = Decimal(asset.current_price)
    threshold = alert.threshold_value

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
    result_obj = await session.execute(select(User).filter(User.id == alert.user_id))
    user = result_obj.scalar_one_or_none()
    if not user:
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
        current_time = clock_in_zone(user.time_zone)
        if in_quiet_hours(user.quiet_hours_start, user.quiet_hours_end, current_time):
            logger.info(f"Alert {alert.id} suppressed due to quiet hours")
            return

    portfolio_value = None
    if alert.condition_type in _PORTFOLIO_CONDITIONS:
        snap = await _portfolio_snapshot(alert, session)
        if snap is None:
            return
        portfolio, priced = snap
        if not portfolio_level_met(
            current_value=portfolio.current_value,
            priced_holdings=priced,
            calculated_at=portfolio.last_calculated_at,
            now=datetime.utcnow(),
            condition=alert.condition_type,
            threshold=alert.threshold_value,
        ):
            return
        asset = None
        portfolio_value = portfolio.current_value
        label = "PORTFOLIO"
        message = alert.custom_message or (
            f"MarketEye Alert: portfolio value is ${portfolio_value} "
            f"({_condition_text(alert)})."
        )
        email_ctx = build_portfolio_alert_email_context(
            user=user,
            alert=alert,
            current_value=portfolio_value,
            frontend_base_url=settings.FRONTEND_BASE_URL,
        )
    else:
        result_obj = await session.execute(select(Asset).filter(Asset.id == alert.asset_id))
        asset = result_obj.scalar_one_or_none()
        if not asset:
            return
        label = asset.symbol
        message = alert.custom_message or _build_alert_message(alert, asset)
        email_ctx = build_alert_email_context(
            user=user,
            asset=asset,
            alert=alert,
            frontend_base_url=settings.FRONTEND_BASE_URL,
        )
    subject = email_ctx.email_subject

    send_result = await _dispatch_alert_notifications(
        alert, user, asset, message, portfolio_value=portfolio_value
    )

    delivered = send_result.get("status") == "sent"
    if not delivered:
        logger.warning(
            "Alert %s notification issue for %s: %s",
            alert.id,
            label,
            send_result,
        )

    log_entry = NotificationLog(
        user_id=user.id,
        alert_id=alert.id,
        asset_id=asset.id if asset is not None else None,
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
        logger.info(f"Triggered alert {alert.id} for {label}")
    else:
        logger.info(f"Alert {alert.id} for {label} stays active after a failed send")


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
