"""
Workspace and WorkspaceMember models for multi-tenancy
"""
import enum
from sqlalchemy import (
    Column,
    String,
    Boolean,
    Integer,
    ForeignKey,
    Enum,
    Index,
    DateTime,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from app.models.base import Base


class PlanType(str, enum.Enum):
    """Workspace subscription plan types"""

    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"


class WorkspaceRole(str, enum.Enum):
    """User roles within a workspace"""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class Workspace(Base):
    """Workspace model for multi-tenant architecture"""

    __tablename__ = "workspaces"

    # Basic Information
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text)

    # Billing
    plan_type = Column(Enum(PlanType), default=PlanType.FREE, nullable=False)
    billing_email = Column(String(255))
    stripe_customer_id = Column(String(255), unique=True)
    stripe_subscription_id = Column(String(255))
    trial_ends_at = Column(DateTime(timezone=True))
    subscription_ends_at = Column(DateTime(timezone=True))

    # Plan Limits (cached from config for performance)
    max_monitors = Column(Integer, default=10, nullable=False)
    max_team_members = Column(Integer, default=1, nullable=False)
    max_alert_channels = Column(Integer, default=2, nullable=False)
    check_interval_minimum = Column(Integer, default=300, nullable=False)  # seconds
    data_retention_days = Column(Integer, default=30, nullable=False)

    # Current Usage
    current_monitors_count = Column(Integer, default=0, nullable=False)
    current_members_count = Column(Integer, default=1, nullable=False)
    checks_this_month = Column(Integer, default=0, nullable=False)
    checks_last_reset = Column(DateTime(timezone=True))

    # Settings (JSON for flexibility)
    settings = Column(JSON, default={})
    features = Column(JSON, default=[])  # Enabled feature flags

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_suspended = Column(Boolean, default=False, nullable=False)
    suspension_reason = Column(String(500))

    # Relationships
    members = relationship("WorkspaceMember", back_populates="workspace", cascade="all, delete-orphan")
    monitors = relationship("Monitor", back_populates="workspace", cascade="all, delete-orphan")
    alert_channels = relationship(
        "AlertChannel", back_populates="workspace", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_workspace_stripe_customer", "stripe_customer_id"),
        Index("idx_workspace_plan", "plan_type"),
        Index("idx_workspace_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Workspace {self.name} ({self.slug})>"


class WorkspaceMember(Base):
    """Junction table for workspace membership with roles"""

    __tablename__ = "workspace_members"

    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(Enum(WorkspaceRole), default=WorkspaceRole.MEMBER, nullable=False)

    # Invitation Tracking
    invited_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    invitation_token = Column(String(255))
    invitation_sent_at = Column(DateTime(timezone=True))
    invitation_accepted = Column(Boolean, default=False, nullable=False)
    joined_at = Column(DateTime(timezone=True))

    # Permissions (cached for performance)
    permissions = Column(JSON, default=[])

    # Relationships
    workspace = relationship("Workspace", back_populates="members")
    user = relationship("User", back_populates="workspace_memberships", foreign_keys=[user_id])
    invited_by = relationship("User", foreign_keys=[invited_by_id])

    # Indexes and Constraints
    __table_args__ = (
        Index("idx_workspace_member_workspace", "workspace_id"),
        Index("idx_workspace_member_user", "user_id"),
        Index("idx_workspace_member_unique", "workspace_id", "user_id", unique=True),
    )

    def __repr__(self) -> str:
        return f"<WorkspaceMember workspace={self.workspace_id} user={self.user_id} role={self.role}>"
