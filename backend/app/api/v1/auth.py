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


_PLACEHOLDER_SMTP_VALUES = frozenset(
    {
        "your-email@gmail.com",
        "your-app-specific-password",
        "your-email",
        "changeme",
        "password",
    }
)


def _smtp_configured() -> bool:
    user = (settings.SMTP_USER or "").strip()
    password = (settings.SMTP_PASSWORD or "").strip()
    if not user or not password:
        return False
    if user.lower() in _PLACEHOLDER_SMTP_VALUES or password.lower() in _PLACEHOLDER_SMTP_VALUES:
        return False
    if user.startswith("your-") or "example.com" in user:
        return False
    return True


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
    When SMTP is not configured and DEBUG/development is on, includes reset_link for local testing.
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
        html = (
            f'<p>You requested a password reset.</p>'
            f'<p><a href="{link}">Reset your password</a> '
            f"(expires in {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes).</p>"
            f"<p>If you did not request this, ignore this email.</p>"
        )
        if _smtp_configured():
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
                "Password reset for %s (SMTP not configured). Link: %s",
                user.email,
                link,
            )
            if _dev_reset_link_allowed():
                reset_link = link
                detail = (
                    "SMTP is not configured. Use the reset link below (development only)."
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
