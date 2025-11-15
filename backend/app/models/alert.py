"""
Alert models for multi-channel alerting system
"""
import enum
from sqlalchemy import Column, String, Integer, ForeignKey, Index, DateTime, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from app.models.base import Base


class AlertChannelType(str, enum.Enum):
    """Types of alert channels"""

    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"
    SMS = "sms"
    PAGERDUTY = "pagerduty"
    DISCORD = "discord"
    TEAMS = "teams"
    TELEGRAM = "telegram"


class AlertChannel(Base):
    """Alert delivery channel configuration"""

    __tablename__ = "alert_channels"

    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )

    # Basic Information
    name = Column(String(255), nullable=False)
    description = Column(Text)
    channel_type = Column(Enum(AlertChannelType), nullable=False)

    # Channel Configuration (varies by type)
    config = Column(JSON, nullable=False)
    # Examples:
    # Email: {"recipients": ["user@example.com"], "cc": [], "bcc": []}
    # Webhook: {"url": "https://...", "headers": {}, "method": "POST"}
    # Slack: {"webhook_url": "https://hooks.slack.com/...", "channel": "#alerts"}
    # SMS: {"phone_numbers": ["+1234567890"]}
    # PagerDuty: {"integration_key": "..."}

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    verification_token = Column(String(255))
    verified_at = Column(DateTime(timezone=True))

    # Usage Tracking
    last_used_at = Column(DateTime(timezone=True))
    total_alerts_sent = Column(Integer, default=0, nullable=False)
    total_alerts_failed = Column(Integer, default=0, nullable=False)

    # Rate Limiting (per channel)
    max_alerts_per_hour = Column(Integer, default=60)
    alerts_sent_this_hour = Column(Integer, default=0, nullable=False)
    rate_limit_reset_at = Column(DateTime(timezone=True))

    # Relationships
    workspace = relationship("Workspace", back_populates="alert_channels")
    alert_rules = relationship("AlertRule", back_populates="alert_channel")
    alert_logs = relationship("AlertLog", back_populates="alert_channel")

    # Indexes
    __table_args__ = (
        Index("idx_alert_channel_workspace", "workspace_id"),
        Index("idx_alert_channel_type", "channel_type"),
    )

    def __repr__(self) -> str:
        return f"<AlertChannel {self.name} ({self.channel_type.value})>"


class AlertRule(Base):
    """Rules for when and how to send alerts"""

    __tablename__ = "alert_rules"

    monitor_id = Column(
        UUID(as_uuid=True), ForeignKey("monitors.id", ondelete="CASCADE"), nullable=False
    )
    alert_channel_id = Column(
        UUID(as_uuid=True), ForeignKey("alert_channels.id", ondelete="CASCADE"), nullable=False
    )

    # Rule Name
    name = Column(String(255))
    description = Column(Text)

    # Alert Conditions
    alert_on_status_change = Column(Boolean, default=True, nullable=False)
    alert_on_slow_response = Column(Boolean, default=False, nullable=False)
    slow_response_threshold_ms = Column(Integer)
    alert_on_ssl_expiry = Column(Boolean, default=True, nullable=False)
    ssl_expiry_threshold_days = Column(Integer, default=30)

    # Custom Conditions (JSON for advanced rules)
    custom_conditions = Column(JSON, default=[])

    # Notification Settings
    notify_on_recovery = Column(Boolean, default=True, nullable=False)
    min_failures_before_alert = Column(Integer, default=2, nullable=False)  # Consecutive failures
    cooldown_minutes = Column(Integer, default=15, nullable=False)  # Don't spam alerts

    # Escalation
    escalation_enabled = Column(Boolean, default=False, nullable=False)
    escalation_minutes = Column(Integer, default=30)  # Escalate if not resolved
    escalation_channel_id = Column(
        UUID(as_uuid=True), ForeignKey("alert_channels.id", ondelete="SET NULL")
    )

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Tracking
    last_alert_sent_at = Column(DateTime(timezone=True))
    total_alerts_sent = Column(Integer, default=0, nullable=False)

    # Relationships
    monitor = relationship("Monitor", back_populates="alert_rules")
    alert_channel = relationship("AlertChannel", back_populates="alert_rules", foreign_keys=[alert_channel_id])
    escalation_channel = relationship("AlertChannel", foreign_keys=[escalation_channel_id])

    # Indexes
    __table_args__ = (
        Index("idx_alert_rule_monitor", "monitor_id"),
        Index("idx_alert_rule_channel", "alert_channel_id"),
    )

    def __repr__(self) -> str:
        return f"<AlertRule for Monitor {self.monitor_id} via Channel {self.alert_channel_id}>"


class AlertLog(Base):
    """Log of all alerts sent"""

    __tablename__ = "alert_logs"

    incident_id = Column(UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"))
    monitor_id = Column(UUID(as_uuid=True), ForeignKey("monitors.id", ondelete="CASCADE"), nullable=False)
    alert_channel_id = Column(
        UUID(as_uuid=True), ForeignKey("alert_channels.id", ondelete="SET NULL")
    )

    # Alert Details
    alert_type = Column(String(50), nullable=False)  # new, resolved, acknowledged, escalated
    severity = Column(String(20))
    message = Column(Text)

    # Delivery
    sent_at = Column(DateTime(timezone=True), nullable=False)
    delivered_at = Column(DateTime(timezone=True))
    success = Column(Boolean, nullable=False)
    error_message = Column(Text)
    retry_count = Column(Integer, default=0, nullable=False)

    # Response (for webhooks, etc.)
    response_status_code = Column(Integer)
    response_body = Column(Text)
    response_time_ms = Column(Integer)

    # Metadata
    metadata = Column(JSON, default={})

    # Relationships
    incident = relationship("Incident", back_populates="alert_logs")
    monitor = relationship("Monitor")
    alert_channel = relationship("AlertChannel", back_populates="alert_logs")

    # Indexes
    __table_args__ = (
        Index("idx_alert_log_incident", "incident_id"),
        Index("idx_alert_log_monitor", "monitor_id", "sent_at"),
        Index("idx_alert_log_channel", "alert_channel_id", "sent_at"),
        Index("idx_alert_log_sent", "sent_at"),
    )

    def __repr__(self) -> str:
        return f"<AlertLog {self.alert_type} at {self.sent_at} - {'Success' if self.success else 'Failed'}>"
