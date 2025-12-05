"""
Notification endpoints - for browser push notifications and notification history.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime
from app.core.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.notification import NotificationLog, EventType, NotificationStatus
from app.models.asset import Asset

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


class TestNotificationRequest(BaseModel):
    """Request for testing notifications."""
    channel: str = "PUSH"  # PUSH, EMAIL, SMS
    message: Optional[str] = None


@router.post("/test")
async def send_test_notification(
    request: TestNotificationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Send a test notification to verify notification setup.
    For PUSH notifications, this returns data for the frontend to show.
    """
    message = request.message or "This is a test notification from MarketEye!"
    
    if request.channel == "PUSH":
        # For push notifications, we return data for the frontend to display
        return {
            "status": "success",
            "channel": "PUSH",
            "data": {
                "title": "🔔 MarketEye Test",
                "body": message,
                "timestamp": datetime.utcnow().isoformat(),
            }
        }
    
    # For other channels, use the notification service
    from app.services.notifications import notification_service
    
    recipient = None
    if request.channel == "EMAIL":
        recipient = current_user.email
    elif request.channel in ["SMS", "CALL"]:
        recipient = current_user.phone_number
        if not recipient:
            raise HTTPException(status_code=400, detail="Phone number not configured")
    
    result = await notification_service.send_notification(
        channel=request.channel,
        to=recipient,
        message=message,
        subject="MarketEye Test Notification"
    )
    
    # Log the notification
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
        "result": result
    }

