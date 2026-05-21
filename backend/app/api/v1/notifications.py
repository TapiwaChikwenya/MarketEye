"""
Notification endpoints - browser push via SSE, test, and notification history.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime

from app.core.deps import get_db, get_current_active_user
from app.core.security import decode_access_token
from app.models.user import User
from app.models.notification import NotificationLog, EventType, NotificationStatus
from app.models.asset import Asset
from app.services.sse import subscribe_alerts, publish_alert

router = APIRouter()


class NotificationResponse(BaseModel):
    """Notification response schema."""
    id: str
    event_type: str
    status: str
    subject: Optional[str]
    message: str
    symbol: Optional[str] = None
    asset_name: Optional[str] = None
    created_at: datetime
    sent_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NotificationSummary(BaseModel):
    """Summary of notifications."""
    total: int
    sent: int
    failed: int
    recent: List[NotificationResponse]


@router.get("/", response_model=List[NotificationResponse])
async def get_notifications(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get notification history for current user."""
    result = await db.execute(
        select(NotificationLog)
        .filter(NotificationLog.user_id == current_user.id)
        .order_by(NotificationLog.created_at.desc())
        .limit(limit)
    )
    notifications = result.scalars().all()
    
    response = []
    for notif in notifications:
        # Get asset info if available
        symbol = None
        asset_name = None
        if notif.asset_id:
            asset_result = await db.execute(
                select(Asset).filter(Asset.id == notif.asset_id)
            )
            asset = asset_result.scalar_one_or_none()
            if asset:
                symbol = asset.symbol
                asset_name = asset.name
        
        response.append(NotificationResponse(
            id=str(notif.id),
            event_type=notif.event_type.value if hasattr(notif.event_type, 'value') else str(notif.event_type),
            status=notif.status.value if hasattr(notif.status, 'value') else str(notif.status),
            subject=notif.subject,
            message=notif.message,
            symbol=symbol,
            asset_name=asset_name,
            created_at=notif.created_at,
            sent_at=notif.sent_at,
        ))
    
    return response


@router.get("/summary", response_model=NotificationSummary)
async def get_notification_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get notification summary for current user."""
    result = await db.execute(
        select(NotificationLog)
        .filter(NotificationLog.user_id == current_user.id)
    )
    all_notifications = result.scalars().all()
    
    total = len(all_notifications)
    sent = sum(1 for n in all_notifications if n.status == NotificationStatus.SENT)
    failed = sum(1 for n in all_notifications if n.status == NotificationStatus.FAILED)
    
    # Get recent 10
    recent_result = await db.execute(
        select(NotificationLog)
        .filter(NotificationLog.user_id == current_user.id)
        .order_by(NotificationLog.created_at.desc())
        .limit(10)
    )
    recent_notifications = recent_result.scalars().all()
    
    recent = []
    for notif in recent_notifications:
        symbol = None
        asset_name = None
        if notif.asset_id:
            asset_result = await db.execute(
                select(Asset).filter(Asset.id == notif.asset_id)
            )
            asset = asset_result.scalar_one_or_none()
            if asset:
                symbol = asset.symbol
                asset_name = asset.name
        
        recent.append(NotificationResponse(
            id=str(notif.id),
            event_type=notif.event_type.value if hasattr(notif.event_type, 'value') else str(notif.event_type),
            status=notif.status.value if hasattr(notif.status, 'value') else str(notif.status),
            subject=notif.subject,
            message=notif.message,
            symbol=symbol,
            asset_name=asset_name,
            created_at=notif.created_at,
            sent_at=notif.sent_at,
        ))
    
    return NotificationSummary(
        total=total,
        sent=sent,
        failed=failed,
        recent=recent
    )


@router.get("/stream")
async def notification_stream(
    request: Request,
    token: str = Query(...),
):
    """SSE endpoint that streams triggered alerts to the browser.

    The browser connects with ``EventSource('/api/v1/notifications/stream?token=...')``
    and receives JSON payloads for each alert that fires for the authenticated user.
    """
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    async def event_generator():
        async for chunk in subscribe_alerts(user_id):
            if await request.is_disconnected():
                break
            yield chunk

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


class TestNotificationRequest(BaseModel):
    """Request for testing notifications."""
    channel: str = "PUSH"
    message: Optional[str] = None


@router.post("/test")
async def send_test_notification(
    request: TestNotificationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Send a test notification.

    For PUSH, publishes to the SSE stream so connected browsers receive it.
    """
    message = request.message or "This is a test notification from MarketEye!"

    if request.channel == "PUSH":
        alert_payload = {
            "user_id": str(current_user.id),
            "type": "test",
            "title": "MarketEye Test",
            "body": message,
            "symbol": "TEST",
            "price": "0.00",
            "condition": "Test notification sent successfully",
            "timestamp": datetime.utcnow().isoformat(),
        }
        await publish_alert(alert_payload)
        return {
            "status": "success",
            "channel": "PUSH",
            "data": {
                "title": alert_payload["title"],
                "body": message,
                "timestamp": alert_payload["timestamp"],
            },
        }

    from app.services.notifications import notification_service

    recipient = None
    if request.channel == "EMAIL":
        recipient = current_user.email
    elif request.channel in ["SMS", "CALL"]:
        recipient = current_user.phone_number
        if not recipient:
            raise HTTPException(status_code=400, detail="Phone number not configured")

    if request.channel == "EMAIL":
        result = await notification_service.send_alert_email(
            to=recipient,
            subject="MarketEye Test Notification",
            body=message,
            symbol="TEST",
            asset_name="Test Asset",
            condition_text="test notification",
            price="0.00",
            triggered_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
        )
    else:
        result = await notification_service.send_notification(
            channel=request.channel,
            to=recipient,
            message=message,
            subject="MarketEye Test Notification",
        )

    log_entry = NotificationLog(
        user_id=current_user.id,
        event_type=EventType.ALERT_TRIGGERED,
        status=NotificationStatus.SENT if result["status"] == "sent" else NotificationStatus.FAILED,
        subject="Test Notification",
        message=message,
        details=result,
        provider=result.get("provider"),
    )
    db.add(log_entry)
    await db.commit()

    return {
        "status": result["status"],
        "channel": request.channel,
        "result": result,
    }

