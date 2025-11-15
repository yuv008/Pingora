"""
User and UserSession models for authentication
"""
from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base


class User(Base):
    """User model for authentication and profile"""

    __tablename__ = "users"

    # Basic Information
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))

    # Account Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)

    # Email Verification
    email_verification_token = Column(String(255))
    email_verification_sent_at = Column(DateTime(timezone=True))

    # Password Reset
    password_reset_token = Column(String(255))
    password_reset_expires = Column(DateTime(timezone=True))

    # Multi-Factor Authentication
    mfa_enabled = Column(Boolean, default=False, nullable=False)
    mfa_secret = Column(String(255))

    # Session Management
    active_sessions = Column(Integer, default=0, nullable=False)
    last_login_at = Column(DateTime(timezone=True))
    last_login_ip = Column(String(45))

    # Rate Limiting
    api_calls_today = Column(Integer, default=0, nullable=False)
    api_calls_reset_at = Column(DateTime(timezone=True))

    # Security
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True))

    # Relationships
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    workspace_memberships = relationship(
        "WorkspaceMember", back_populates="user", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_user_email_active", "email", "is_active"),
        Index("idx_user_username_active", "username", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class UserSession(Base):
    """User session for tracking active logins"""

    __tablename__ = "user_sessions"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Session Tokens
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    refresh_token = Column(String(255), unique=True, nullable=False, index=True)

    # Session Details
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    device_fingerprint = Column(String(255))

    # Expiration
    access_expires_at = Column(DateTime(timezone=True), nullable=False)
    refresh_expires_at = Column(DateTime(timezone=True), nullable=False)

    # Activity Tracking
    last_activity = Column(DateTime(timezone=True))
    requests_count = Column(Integer, default=0, nullable=False)

    # Security
    is_active = Column(Boolean, default=True, nullable=False)
    revoked_at = Column(DateTime(timezone=True))
    revoked_reason = Column(String(255))

    # Relationships
    user = relationship("User", back_populates="sessions")

    # Indexes
    __table_args__ = (
        Index("idx_session_user_active", "user_id", "is_active"),
        Index("idx_session_expires", "refresh_expires_at"),
    )

    def __repr__(self) -> str:
        return f"<UserSession {self.session_token[:8]}... for user {self.user_id}>"
