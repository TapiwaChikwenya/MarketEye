"""
HTML email templates for transactional and alert notifications.
"""


def build_alert_email_html(
    *,
    symbol: str,
    asset_name: str,
    message: str,
    condition_text: str,
    price: str,
    triggered_at: str,
) -> str:
    """Mobile-friendly HTML for price alert emails (inline CSS subset)."""
    title = f"MarketEye Alert: {symbol}"
    return f"""
<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f7f5f1;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f7f5f1;padding:40px 16px;">
    <tr><td align="center">
      <table role="presentation" width="100%" style="max-width:560px;background:#fff;border-radius:12px;border:1px solid rgba(15,23,42,.06);">
        <tr><td style="padding:32px 32px 0;">
          <div style="display:inline-block;background:linear-gradient(135deg,#1d4ed8,#1e293b);padding:8px 14px;border-radius:8px;color:#fff;font-weight:600;font-size:14px;letter-spacing:.04em;">MarketEye</div>
        </td></tr>
        <tr><td style="padding:24px 32px;">
          <h1 style="margin:0 0 8px;font-size:22px;color:#0f172a;font-weight:600;">{title}</h1>
          <p style="margin:0 0 20px;font-size:14px;color:#64748b;">{asset_name}</p>
          <p style="margin:0 0 16px;font-size:15px;line-height:1.6;color:#475569;">{message}</p>
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f8fafc;border-radius:8px;margin:0 0 20px;">
            <tr>
              <td style="padding:16px 20px;">
                <p style="margin:0 0 4px;font-size:12px;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;">Condition</p>
                <p style="margin:0;font-size:15px;color:#0f172a;font-weight:600;">{condition_text}</p>
              </td>
              <td style="padding:16px 20px;border-left:1px solid rgba(15,23,42,.06);">
                <p style="margin:0 0 4px;font-size:12px;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;">Price</p>
                <p style="margin:0;font-size:15px;color:#0f172a;font-weight:600;">${price}</p>
              </td>
            </tr>
          </table>
          <p style="margin:0;font-size:12px;color:#94a3b8;">Triggered at {triggered_at} UTC</p>
        </td></tr>
        <tr><td style="padding:16px 32px 28px;border-top:1px solid rgba(15,23,42,.06);">
          <p style="margin:0;font-size:12px;line-height:1.6;color:#94a3b8;">
            You are receiving this because a MarketEye alert rule matched. Not investment advice.
          </p>
        </td></tr>
      </table>
      <p style="margin:16px 0 0;font-size:12px;color:#94a3b8;">&copy; MarketEye</p>
    </td></tr>
  </table>
</body></html>
""".strip()
