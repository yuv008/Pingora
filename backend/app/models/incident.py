"""
Incident models for tracking monitor failures and outages
"""
import enum
from sqlalchemy import Column, String, Integer, ForeignKey, Index, DateTime, Text, Boolean, Enum
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from app.models.base import Base


class IncidentStatus(str, enum.Enum):
    """Incident status"""

    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    INVESTIGATING = "investigating"
    IDENTIFIED = "identified"
    MONITORING = "monitoring"
    RESOLVED = "resolved"


class IncidentSeverity(str, enum.Enum):
    """Incident severity levels"""

    CRITICAL = "critical"  # Complete outage
    HIGH = "high"  # Major functionality impaired
    MEDIUM = "medium"  # Partial functionality issues
    LOW = "low"  # Minor issues
    INFO = "info"  # Informational


class Incident(Base):
    """Incident tracking for monitor failures"""

    __tablename__ = "incidents"

    monitor_id = Column(
        UUID(as_uuid=True), ForeignKey("monitors.id", ondelete="CASCADE"), nullable=False
    )

    # Incident Timeline
    started_at = Column(DateTime(timezone=True), nullable=False)
    detected_at = Column(DateTime(timezone=True))  # When system detected it
    acknowledged_at = Column(DateTime(timezone=True))
    resolved_at = Column(DateTime(timezone=True))

    # Status & Severity
    status = Column(Enum(IncidentStatus), default=IncidentStatus.OPEN, nullable=False)
    severity = Column(Enum(IncidentSeverity), default=IncidentSeverity.CRITICAL, nullable=False)

    # Incident Details
    title = Column(String(255))
    trigger_type = Column(String(50))  # status_code, timeout, ssl_expiry, etc.
    error_message = Column(Text)
    description = Column(Text)

    # Metrics
    total_checks_failed = Column(Integer, default=1, nullable=False)
    affected_regions = Column(JSON, default=[])

    # Check Results (store initial and resolution checks)
    initial_check_result = Column(JSON)
    resolution_check_result = Column(JSON)

    # Notifications
    notifications_sent = Column(JSON, default=[])  # Track what notifications were sent
    notification_count = Column(Integer, default=0, nullable=False)

    # Acknowledgment
    acknowledged_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))

    # Resolution
    resolved_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    resolution_notes = Column(Text)
    auto_resolved = Column(Boolean, default=False, nullable=False)

    # Impact (calculated)
    downtime_seconds = Column(Integer)  # Total downtime duration
    mttr_seconds = Column(Integer)  # Mean Time To Recovery

    # Public Status Page
    show_on_status_page = Column(Boolean, default=True, nullable=False)
    public_message = Column(Text)

    # Relationships
    monitor = relationship("Monitor", back_populates="incidents")
    acknowledged_by = relationship("User", foreign_keys=[acknowledged_by_id])
    resolved_by = relationship("User", foreign_keys=[resolved_by_id])
    updates = relationship("IncidentUpdate", back_populates="incident", cascade="all, delete-orphan")
    alert_logs = relationship("AlertLog", back_populates="incident")

    # Indexes
    __table_args__ = (
        Index("idx_incident_monitor", "monitor_id"),
        Index("idx_incident_status", "status"),
        Index("idx_incident_started", "started_at"),
        Index("idx_incident_unresolved", "monitor_id", "status", postgresql_where=(status != "resolved")),
    )

    def __repr__(self) -> str:
        return f"<Incident {self.id} for Monitor {self.monitor_id} - {self.status.value}>"


class IncidentUpdate(Base):
    """Updates/comments on an incident"""

    __tablename__ = "incident_updates"

    incident_id = Column(
        UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))

    # Update Details
    status = Column(Enum(IncidentStatus))
    message = Column(Text, nullable=False)
    update_type = Column(String(50), default="comment")  # comment, status_change, notification

    # Visibility
    is_public = Column(Boolean, default=False, nullable=False)  # Show on status page

    # Relationships
    incident = relationship("Incident", back_populates="updates")
    user = relationship("User")

    # Indexes
    __table_args__ = (Index("idx_incident_update_incident", "incident_id", "created_at"),)

    def __repr__(self) -> str:
        return f"<IncidentUpdate {self.id} for Incident {self.incident_id}>"
