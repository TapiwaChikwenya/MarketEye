"""
Authentication endpoints.
"""
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.deps import get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_password_reset_token,
    decode_password_reset_token,
)
from app.models.user import User
from app.schemas.user import (
    UserCreate,
    UserResponse,
    Token,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
)
from app.services.notifications import notification_service

logger = logging.getLogger(__name__)

router = APIRouter()


def _email_configured() -> bool:
    """
    True when a real-looking SendGrid API key is set in the environment.

    SendGrid API keys always start with "SG." and are roughly 69 chars long.
    Rejecting short or placeholder values keeps dev environments in demo
    mode automatically, so /forgot-password still returns the reset link
    in the JSON response when DEBUG=True.
    """
    key = (settings.SENDGRID_API_KEY or "").strip()
    return key.startswith("SG.") and len(key) > 30


def _dev_reset_link_allowed() -> bool:
    return settings.DEBUG or settings.ENVIRONMENT == "development"


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user."""
    # Check if user already exists
    result = await db.execute(select(User).filter(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        name=user_data.name,
        phone_number=user_data.phone_number,
        hashed_password=hashed_password,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Login user and return access token."""
    # Find user by email
    result = await db.execute(select(User).filter(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Request a password reset email. Response is identical whether or not the email exists.
    When SendGrid is not configured and DEBUG/development is on, includes reset_link for local testing.
    """
    detail = (
        "If an account exists for this email, you will receive reset instructions shortly."
    )
    reset_link: Optional[str] = None

    result = await db.execute(select(User).filter(User.email == str(body.email)))
    user = result.scalar_one_or_none()
    if user and user.is_active:
        token = create_password_reset_token(str(user.id))
        base = settings.FRONTEND_BASE_URL.rstrip("/")
        link = f"{base}/reset-password?token={token}"
        subj = "Reset your MarketEye password"
        plain = (
            f"You requested a password reset. Open this link (valid for "
            f"{settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes):\n\n{link}\n\n"
            "If you did not request this, you can ignore this email."
        )
        html = f"""
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
          <h1 style="margin:0 0 12px;font-size:22px;color:#0f172a;font-weight:600;">Reset your password</h1>
          <p style="margin:0 0 24px;font-size:15px;line-height:1.6;color:#475569;">
            We received a request to reset the password for your MarketEye account.
            Click the button below to choose a new one. This link expires in
            {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes.
          </p>
          <a href="{link}" style="display:inline-block;background:#1d4ed8;color:#fff;text-decoration:none;font-weight:600;padding:12px 24px;border-radius:8px;font-size:15px;">Reset password</a>
          <p style="margin:24px 0 0;font-size:13px;line-height:1.6;color:#94a3b8;">
            Or paste this link into your browser:<br>
            <a href="{link}" style="color:#1d4ed8;word-break:break-all;">{link}</a>
          </p>
        </td></tr>
        <tr><td style="padding:16px 32px 28px;border-top:1px solid rgba(15,23,42,.06);">
          <p style="margin:16px 0 0;font-size:12px;line-height:1.6;color:#94a3b8;">
            Didn't request this? You can safely ignore the email - your password won't change.
          </p>
        </td></tr>
      </table>
      <p style="margin:16px 0 0;font-size:12px;color:#94a3b8;">&copy; MarketEye &middot; Not investment advice</p>
    </td></tr>
  </table>
</body></html>
""".strip()
        if _email_configured():
            sent = await notification_service.send_email(user.email, subj, plain, html=html)
            if sent.get("status") != "sent":
                logger.warning("Password reset email may not have been sent: %s", sent)
                if _dev_reset_link_allowed():
                    reset_link = link
                    detail = (
                        "Email could not be sent. Use the reset link below (development only)."
                    )
        else:
            logger.info(
                "Password reset for %s (SendGrid not configured). Link: %s",
                user.email,
                link,
            )
            if _dev_reset_link_allowed():
                reset_link = link
                detail = (
                    "SendGrid is not configured. Use the reset link below (development only)."
                )

    return ForgotPasswordResponse(detail=detail, reset_link=reset_link)


@router.post("/reset-password")
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Set a new password using the token from the reset email."""
    if len(body.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters",
        )

    uid = decode_password_reset_token(body.token)
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset link",
        )

    result = await db.execute(select(User).filter(User.id == uuid.UUID(uid)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset link",
        )

    user.hashed_password = get_password_hash(body.new_password)
    await db.commit()

    return {"detail": "Password updated. You can sign in now."}
