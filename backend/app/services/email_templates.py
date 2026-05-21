"""
HTML and plain-text email templates for MarketEye alert notifications.
"""
from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional
from zoneinfo import ZoneInfo

from app.models.alert import AlertRule, ConditionType, RepeatBehavior
from app.models.asset import Asset, AssetType
from app.models.user import User


@dataclass(frozen=True)
class AlertEmailContext:
    """Structured data for rendering trader-focused alert emails."""

    recipient_name: str
    symbol: str
    asset_name: str
    asset_type: str
    exchange: Optional[str]
    condition_headline: str
    condition_summary: str
    threshold_label: str
    threshold_value: str
    current_price: str
    change_24h: Optional[str]
    change_percent_24h: Optional[str]
    alert_name: Optional[str]
    repeat_behavior_label: str
    triggered_at_display: str
    timezone_label: str
    dashboard_url: str
    email_subject: str
    action_note: str


def _display_name(user: User) -> str:
    if user.name and user.name.strip():
        return user.name.strip()
    local = (user.email or "").split("@")[0]
    return local.replace(".", " ").replace("_", " ").title() if local else "Trader"


def _format_price(value) -> str:
    """Format a market price for display (always 2 decimal places)."""
    if value is None:
        return "—"
    try:
        return f"${Decimal(str(value)):,.2f}"
    except Exception:
        return str(value)


def _format_money(value) -> str:
    """Format threshold / level values (compact when whole dollars)."""
    if value is None:
        return "—"
    try:
        d = Decimal(str(value))
        if d == d.to_integral_value():
            return f"{int(d):,}"
        return f"{d:,.2f}".rstrip("0").rstrip(".")
    except Exception:
        return str(value)


def _format_signed_percent(value) -> Optional[str]:
    if value is None:
        return None
    try:
        d = Decimal(str(value))
        sign = "+" if d > 0 else ""
        return f"{sign}{d:.2f}%"
    except Exception:
        return None


def _format_signed_change(value) -> Optional[str]:
    if value is None:
        return None
    try:
        d = Decimal(str(value))
        sign = "+" if d > 0 else ""
        return f"{sign}${abs(d):,.2f}"
    except Exception:
        return None


def _condition_copy(alert: AlertRule, asset: Asset) -> tuple[str, str, str, str]:
    """Return headline, summary, threshold label, threshold value."""
    threshold = _format_money(alert.threshold_value)
    price = _format_price(asset.current_price)
    symbol = asset.symbol

    if alert.condition_type == ConditionType.PRICE_ABOVE:
        return (
            f"{symbol} crossed above your target price",
            f"{symbol} is now <strong>${price}</strong>, above your alert level of "
            f"<strong>${threshold}</strong>. Consider whether to take profit, trail a stop, "
            f"or wait for continuation before adding exposure.",
            "Target price",
            f"${threshold}",
        )
    if alert.condition_type == ConditionType.PRICE_BELOW:
        return (
            f"{symbol} fell below your watch level",
            f"{symbol} is now <strong>${price}</strong>, below your alert level of "
            f"<strong>${threshold}</strong>. Review support, risk limits, and whether this "
            f"is a dip to watch or a breakdown to act on.",
            "Watch level",
            f"${threshold}",
        )
    if alert.condition_type == ConditionType.PERCENT_CHANGE_UP:
        pct = _format_signed_percent(asset.change_percent_24h) or "—"
        return (
            f"{symbol} 24h move exceeded your upside threshold",
            f"{symbol} is up <strong>{pct}</strong> over 24h (alert: <strong>{threshold}%</strong> or more). "
            f"Last price <strong>${price}</strong>. Momentum may be extending — confirm volume "
            f"and news before chasing.",
            "24h % threshold",
            f"{threshold}%",
        )
    if alert.condition_type == ConditionType.PERCENT_CHANGE_DOWN:
        pct = _format_signed_percent(asset.change_percent_24h) or "—"
        return (
            f"{symbol} 24h decline exceeded your downside threshold",
            f"{symbol} is down <strong>{pct}</strong> over 24h (alert: <strong>{threshold}%</strong> or more). "
            f"Last price <strong>${price}</strong>. Check whether this is a pullback in a trend "
            f"or risk that needs hedging.",
            "24h % threshold",
            f"{threshold}%",
        )
    return (
        f"{symbol} alert condition met",
        f"Your rule for {symbol} matched at <strong>${price}</strong>.",
        "Threshold",
        str(alert.threshold_value),
    )


def _repeat_behavior_label(behavior: RepeatBehavior) -> str:
    return {
        RepeatBehavior.ONE_TIME: "One-time (alert will deactivate)",
        RepeatBehavior.ONCE_PER_DAY: "At most once per day",
        RepeatBehavior.ONCE_PER_HOUR: "At most once per hour",
        RepeatBehavior.UNLIMITED: "Repeats whenever condition is met",
    }.get(behavior, str(behavior))


def _triggered_timestamp(user: User) -> tuple[str, str]:
    now = datetime.utcnow()
    tz_name = (user.time_zone or "UTC").strip() or "UTC"
    try:
        z = ZoneInfo(tz_name)
        local = now.replace(tzinfo=ZoneInfo("UTC")).astimezone(z)
        return local.strftime("%A, %b %d, %Y at %I:%M %p"), tz_name
    except Exception:
        return now.strftime("%A, %b %d, %Y at %H:%M UTC"), "UTC"


def _asset_type_label(asset_type: AssetType) -> str:
    return {
        AssetType.STOCK: "Stock",
        AssetType.CRYPTO: "Crypto",
        AssetType.ETF: "ETF",
        AssetType.MUTUAL_FUND: "Mutual fund",
        AssetType.INDEX: "Index",
    }.get(asset_type, str(asset_type))


def build_demo_alert_email_context(user: User, frontend_base_url: str) -> AlertEmailContext:
    """Sample alert context for /notifications/test (EMAIL channel)."""
    triggered_at, tz_label = _triggered_timestamp(user)
    base = frontend_base_url.rstrip("/")
    return AlertEmailContext(
        recipient_name=_display_name(user),
        symbol="DEMO",
        asset_name="Demo Asset (test notification)",
        asset_type="Stock",
        exchange="NASDAQ",
        condition_headline="DEMO crossed above your target price",
        condition_summary=(
            "This is a <strong>test alert</strong> from MarketEye. When a real rule fires, "
            "you will see the live ticker, trigger price, and 24h move here."
        ),
        threshold_label="Target price",
        threshold_value="$100.00",
        current_price="$105.25",
        change_24h="+$2.50",
        change_percent_24h="+2.43%",
        alert_name="Test notification",
        repeat_behavior_label="Test only (not a live rule)",
        triggered_at_display=triggered_at,
        timezone_label=tz_label,
        dashboard_url=f"{base}/dashboard",
        email_subject="DEMO alert — test notification (MarketEye)",
        action_note="Open your dashboard to manage alerts and watchlists.",
    )


def build_alert_email_context(
    *,
    user: User,
    asset: Asset,
    alert: AlertRule,
    frontend_base_url: str,
) -> AlertEmailContext:
    """Build template context from user, asset, and alert rule."""
    headline, summary, threshold_label, threshold_value = _condition_copy(alert, asset)
    triggered_at, tz_label = _triggered_timestamp(user)
    base = frontend_base_url.rstrip("/")
    dashboard_url = f"{base}/dashboard"

    subject_symbol = asset.symbol
    if alert.condition_type in (
        ConditionType.PRICE_ABOVE,
        ConditionType.PRICE_BELOW,
    ):
        subject_action = f"at {_format_price(asset.current_price)}"
    else:
        subject_action = _format_signed_percent(asset.change_percent_24h) or "triggered"

    return AlertEmailContext(
        recipient_name=_display_name(user),
        symbol=asset.symbol,
        asset_name=asset.name or asset.symbol,
        asset_type=_asset_type_label(asset.asset_type),
        exchange=asset.exchange,
        condition_headline=headline,
        condition_summary=summary,
        threshold_label=threshold_label,
        threshold_value=threshold_value,
        current_price=_format_price(asset.current_price),
        change_24h=_format_signed_change(asset.change_24h),
        change_percent_24h=_format_signed_percent(asset.change_percent_24h),
        alert_name=alert.name,
        repeat_behavior_label=_repeat_behavior_label(alert.repeat_behavior),
        triggered_at_display=triggered_at,
        timezone_label=tz_label,
        dashboard_url=dashboard_url,
        email_subject=f"{subject_symbol} alert — {subject_action}",
        action_note=(
            f"Open your dashboard to review {asset.symbol} charts, other alerts, "
            f"and adjust this rule if needed."
        ),
    )


def build_alert_email_plain(ctx: AlertEmailContext) -> str:
    """Plain-text body for alert emails (inbox preview + non-HTML clients)."""
    lines = [
        f"Hi {ctx.recipient_name},",
        "",
        f"Your MarketEye alert fired for {ctx.symbol} ({ctx.asset_name}).",
        "",
        ctx.condition_headline,
        "",
        f"  Ticker:        {ctx.symbol}",
        f"  Asset:         {ctx.asset_name} ({ctx.asset_type})",
    ]
    if ctx.exchange:
        lines.append(f"  Exchange:      {ctx.exchange}")
    lines.extend(
        [
            f"  Last price:    {ctx.current_price}",
            f"  {ctx.threshold_label}:  {ctx.threshold_value}",
        ]
    )
    if ctx.change_percent_24h:
        lines.append(f"  24h change:    {ctx.change_percent_24h}")
    if ctx.change_24h:
        lines.append(f"  24h $ change:  {ctx.change_24h}")
    if ctx.alert_name:
        lines.append(f"  Alert name:    {ctx.alert_name}")
    lines.extend(
        [
            f"  Repeat:        {ctx.repeat_behavior_label}",
            "",
            f"Triggered: {ctx.triggered_at_display} ({ctx.timezone_label})",
            "",
            ctx.action_note,
            f"Dashboard: {ctx.dashboard_url}",
            "",
            "— MarketEye · Not investment advice",
        ]
    )
    return "\n".join(lines)


def build_alert_email_html(ctx: AlertEmailContext) -> str:
    """Mobile-friendly HTML alert email for traders."""
    name = html.escape(ctx.recipient_name)
    symbol = html.escape(ctx.symbol)
    asset_name = html.escape(ctx.asset_name)
    asset_type = html.escape(ctx.asset_type)
    exchange_row = ""
    if ctx.exchange:
        exchange_row = f"""
            <tr>
              <td style="padding:8px 0;font-size:14px;color:#64748b;">Exchange</td>
              <td style="padding:8px 0;font-size:14px;color:#0f172a;font-weight:600;text-align:right;">{html.escape(ctx.exchange)}</td>
            </tr>"""
    change_rows = ""
    if ctx.change_percent_24h:
        if ctx.change_percent_24h.startswith("+"):
            change_color = "#16a34a"
        elif ctx.change_percent_24h.startswith("-"):
            change_color = "#dc2626"
        else:
            change_color = "#64748b"
        change_rows += f"""
            <tr>
              <td style="padding:8px 0;font-size:14px;color:#64748b;">24h change</td>
              <td style="padding:8px 0;font-size:14px;color:{change_color};font-weight:600;text-align:right;">{html.escape(ctx.change_percent_24h)}</td>
            </tr>"""
    if ctx.change_24h:
        change_rows += f"""
            <tr>
              <td style="padding:8px 0;font-size:14px;color:#64748b;">24h move</td>
              <td style="padding:8px 0;font-size:14px;color:#0f172a;font-weight:600;text-align:right;">{html.escape(ctx.change_24h)}</td>
            </tr>"""
    alert_name_row = ""
    if ctx.alert_name:
        alert_name_row = f"""
            <tr>
              <td style="padding:8px 0;font-size:14px;color:#64748b;">Alert name</td>
              <td style="padding:8px 0;font-size:14px;color:#0f172a;font-weight:600;text-align:right;">{html.escape(ctx.alert_name)}</td>
            </tr>"""
    summary = ctx.condition_summary  # contains intentional <strong> tags
    headline = html.escape(ctx.condition_headline)
    dashboard_url = html.escape(ctx.dashboard_url)

    return f"""
<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:32px 16px;">
    <tr><td align="center">
      <table role="presentation" width="100%" style="max-width:600px;background:#ffffff;border-radius:12px;border:1px solid #e2e8f0;overflow:hidden;">
        <tr><td style="padding:28px 32px 20px;background:linear-gradient(135deg,#1e3a8a 0%,#0f172a 100%);">
          <div style="font-size:13px;font-weight:600;color:#93c5fd;letter-spacing:.06em;text-transform:uppercase;">MarketEye Alert</div>
          <div style="margin-top:12px;font-size:26px;font-weight:700;color:#ffffff;letter-spacing:-.02em;">{symbol}</div>
          <div style="margin-top:4px;font-size:15px;color:#cbd5e1;">{asset_name} · {asset_type}</div>
        </td></tr>
        <tr><td style="padding:28px 32px 8px;">
          <p style="margin:0 0 16px;font-size:16px;line-height:1.5;color:#334155;">Hi {name},</p>
          <p style="margin:0 0 8px;font-size:18px;line-height:1.4;color:#0f172a;font-weight:600;">{headline}</p>
          <p style="margin:0 0 24px;font-size:15px;line-height:1.65;color:#475569;">{summary}</p>
        </td></tr>
        <tr><td style="padding:0 32px 24px;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;">
            <tr><td style="padding:20px 22px;">
              <p style="margin:0 0 14px;font-size:12px;font-weight:600;color:#64748b;text-transform:uppercase;letter-spacing:.05em;">Market snapshot</p>
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="padding:8px 0;font-size:14px;color:#64748b;">Last price</td>
                  <td style="padding:8px 0;font-size:20px;color:#0f172a;font-weight:700;text-align:right;">{html.escape(ctx.current_price)}</td>
                </tr>
                <tr>
                  <td style="padding:8px 0;font-size:14px;color:#64748b;">{html.escape(ctx.threshold_label)}</td>
                  <td style="padding:8px 0;font-size:14px;color:#0f172a;font-weight:600;text-align:right;">{html.escape(ctx.threshold_value)}</td>
                </tr>
                {change_rows}
                {exchange_row}
              </table>
            </td></tr>
          </table>
        </td></tr>
        <tr><td style="padding:0 32px 24px;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;">
            <tr><td style="padding:18px 22px;">
              <p style="margin:0 0 12px;font-size:12px;font-weight:600;color:#64748b;text-transform:uppercase;letter-spacing:.05em;">Your rule</p>
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                {alert_name_row}
                <tr>
                  <td style="padding:8px 0;font-size:14px;color:#64748b;">Repeat</td>
                  <td style="padding:8px 0;font-size:14px;color:#0f172a;text-align:right;">{html.escape(ctx.repeat_behavior_label)}</td>
                </tr>
                <tr>
                  <td style="padding:8px 0;font-size:14px;color:#64748b;">Triggered</td>
                  <td style="padding:8px 0;font-size:14px;color:#0f172a;text-align:right;">{html.escape(ctx.triggered_at_display)}</td>
                </tr>
                <tr>
                  <td style="padding:8px 0;font-size:14px;color:#64748b;">Timezone</td>
                  <td style="padding:8px 0;font-size:14px;color:#0f172a;text-align:right;">{html.escape(ctx.timezone_label)}</td>
                </tr>
              </table>
            </td></tr>
          </table>
        </td></tr>
        <tr><td style="padding:4px 32px 28px;" align="center">
          <a href="{dashboard_url}" style="display:inline-block;background:#1d4ed8;color:#ffffff;text-decoration:none;font-weight:600;font-size:15px;padding:14px 28px;border-radius:8px;">Open dashboard</a>
          <p style="margin:16px 0 0;font-size:13px;line-height:1.5;color:#64748b;text-align:center;">{html.escape(ctx.action_note)}</p>
        </td></tr>
        <tr><td style="padding:18px 32px 24px;border-top:1px solid #e2e8f0;background:#f8fafc;">
          <p style="margin:0;font-size:12px;line-height:1.6;color:#94a3b8;text-align:center;">
            You received this because a MarketEye alert rule matched. Not investment advice.
            Past performance does not guarantee future results.
          </p>
        </td></tr>
      </table>
      <p style="margin:14px 0 0;font-size:11px;color:#94a3b8;">&copy; MarketEye</p>
    </td></tr>
  </table>
</body></html>
""".strip()
