"""
User schemas.
"""
from typing import Optional
from datetime import time
from pydantic import BaseModel, EmailStr, UUID4, ConfigDict
from app.models.user import ContactMethod, SubscriptionTier


class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    name: Optional[str] = None
    phone_number: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a user."""
    password: str


class UserUpdate(BaseModel):
    """Schema for updating a user."""
    name: Optional[str] = None
    phone_number: Optional[str] = None
    preferred_contact_method: Optional[ContactMethod] = None
    time_zone: Optional[str] = None
    quiet_hours_enabled: Optional[bool] = None
    quiet_hours_start: Optional[time] = None
    quiet_hours_end: Optional[time] = None


class UserResponse(UserBase):
    """Schema for user response."""
    id: UUID4
    preferred_contact_method: ContactMethod
    time_zone: str
    quiet_hours_enabled: bool
    quiet_hours_start: Optional[time]
    quiet_hours_end: Optional[time]
    subscription_tier: SubscriptionTier
    is_active: bool
    is_superuser: bool = False
    email_verified: bool
    phone_verified: bool

    model_config = ConfigDict(from_attributes=True)


class ForgotPasswordRequest(BaseModel):
    """Request password reset email."""
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    """Forgot-password response (reset_link only when dev + SMTP not configured)."""
    detail: str
    reset_link: Optional[str] = None


class ResetPasswordRequest(BaseModel):
    """Reset password with token from email."""
    token: str
    new_password: str


class Token(BaseModel):
    """Token schema."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token data schema."""
    user_id: Optional[str] = None
