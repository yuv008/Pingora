"""
Pydantic schemas for User model
Used for request validation and response serialization
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator


# Request Schemas
class UserRegister(BaseModel):
    """Schema for user registration"""
    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    password: str = Field(..., min_length=8, description="Password")
    full_name: Optional[str] = Field(None, max_length=255, description="Full name")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format"""
        if not v.isalnum() and "_" not in v and "-" not in v:
            raise ValueError("Username must contain only alphanumeric characters, underscores, or hyphens")
        return v.lower()


class UserLogin(BaseModel):
    """Schema for user login - accepts email or username"""
    email: Optional[EmailStr] = Field(None, description="User email address")
    username: Optional[str] = Field(None, description="Username")
    password: str = Field(..., description="Password")

    @field_validator("email", mode="before")
    @classmethod
    def validate_email_or_username(cls, v, info):
        """Ensure either email or username is provided"""
        if not v and not info.data.get("username"):
            raise ValueError("Either email or username must be provided")
        return v


class UserUpdate(BaseModel):
    """Schema for updating user profile"""
    full_name: Optional[str] = Field(None, max_length=255)
    username: Optional[str] = Field(None, min_length=3, max_length=50)


class UserChangePassword(BaseModel):
    """Schema for changing password"""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")


class PasswordReset(BaseModel):
    """Schema for password reset request"""
    email: EmailStr = Field(..., description="User email address")


class PasswordResetConfirm(BaseModel):
    """Schema for confirming password reset"""
    token: str = Field(..., description="Reset token")
    new_password: str = Field(..., min_length=8, description="New password")


class EmailVerification(BaseModel):
    """Schema for email verification"""
    token: str = Field(..., description="Verification token")


# Response Schemas
class UserResponse(BaseModel):
    """Schema for user response"""
    id: str
    email: str
    username: str
    full_name: Optional[str]
    is_active: bool
    email_verified: bool
    mfa_enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }


class TokenResponse(BaseModel):
    """Schema for authentication token response"""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Seconds until token expires")
    user: UserResponse = Field(..., description="User information")


class RefreshTokenRequest(BaseModel):
    """Schema for refreshing access token"""
    refresh_token: str = Field(..., description="Refresh token")


class SessionResponse(BaseModel):
    """Schema for session information"""
    id: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: datetime
    last_activity: Optional[datetime]
    is_active: bool

    model_config = {
        "from_attributes": True
    }


class UserWithSessions(UserResponse):
    """Schema for user with active sessions"""
    active_sessions_count: int
    sessions: list[SessionResponse] = []
