"""
Monitor and MonitorCheck models for API monitoring
"""
import enum
from sqlalchemy import (
    Column,
    String,
    Boolean,
    Integer,
    Float,
    ForeignKey,
    Index,
    DateTime,
    Text,
    BigInteger,
    Date,
    Enum,
)
from sqlalchemy.dialects.postgresql import UUID, JSON, ARRAY
from sqlalchemy.orm import relationship
from app.models.base import Base


class MonitorType(str, enum.Enum):
    """Types of monitors supported"""

    HTTP = "http"
    HTTPS = "https"
    TCP = "tcp"
    UDP = "udp"
    PING = "ping"
    DNS = "dns"
    WEBSOCKET = "websocket"
    GRPC = "grpc"


class MonitorStatus(str, enum.Enum):
    """Current status of a monitor"""

    UP = "up"
    DOWN = "down"
    DEGRADED = "degraded"
    PAUSED = "paused"
    UNKNOWN = "unknown"


class Monitor(Base):
    """Monitor configuration and state"""

    __tablename__ = "monitors"

    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )

    # Basic Information
    name = Column(String(255), nullable=False)
    description = Column(Text)
    monitor_type = Column(Enum(MonitorType), nullable=False, default=MonitorType.HTTPS)

    # Target Configuration
    url = Column(Text, nullable=False)  # URL, hostname, or IP
    method = Column(String(10), default="GET")  # For HTTP/HTTPS
    port = Column(Integer)  # For TCP/UDP

    # Request Configuration (for HTTP/HTTPS)
    headers = Column(JSON, default={})
    body = Column(Text)
    query_params = Column(JSON, default={})

    # Authentication
    auth_type = Column(String(50))  # basic, bearer, oauth2, api_key
    auth_config = Column(JSON, default={})  # Store encrypted credentials

    # Monitoring Configuration
    interval_seconds = Column(Integer, default=300, nullable=False)  # 5 minutes
    timeout_seconds = Column(Integer, default=30, nullable=False)
    retry_count = Column(Integer, default=2, nullable=False)

    # Multi-Region Monitoring
    regions = Column(ARRAY(String), default=["us-east-1"])
    check_from_all_regions = Column(Boolean, default=False, nullable=False)

    # Validation Rules (stored as JSON for flexibility)
    assertions = Column(JSON, default=[])
    expected_status_codes = Column(ARRAY(Integer), default=[200])
    expected_response_time_ms = Column(Integer)
    expected_body_contains = Column(Text)
    expected_body_regex = Column(Text)
    expected_headers = Column(JSON)

    # SSL Certificate Monitoring
    ssl_check_enabled = Column(Boolean, default=True, nullable=False)
    ssl_expiry_warning_days = Column(Integer, default=30, nullable=False)
    ssl_verify = Column(Boolean, default=True, nullable=False)

    # Status & State
    is_active = Column(Boolean, default=True, nullable=False)
    is_paused = Column(Boolean, default=False, nullable=False)
    current_status = Column(Enum(MonitorStatus), default=MonitorStatus.UNKNOWN, nullable=False)

    # Cached Performance Metrics (for quick dashboard display)
    uptime_percentage_24h = Column(Float)
    uptime_percentage_7d = Column(Float)
    uptime_percentage_30d = Column(Float)
    avg_response_time_24h = Column(Float)
    avg_response_time_7d = Column(Float)
    avg_response_time_30d = Column(Float)

    # Scheduling
    last_checked_at = Column(DateTime(timezone=True))
    next_check_at = Column(DateTime(timezone=True))
    last_check_status = Column(String(20))
    last_check_error = Column(Text)

    # Maintenance Windows (JSON array of time ranges)
    maintenance_windows = Column(JSON, default=[])

    # Tags for Organization
    tags = Column(ARRAY(String), default=[])

    # Relationships
    workspace = relationship("Workspace", back_populates="monitors")
    checks = relationship("MonitorCheck", back_populates="monitor", cascade="all, delete-orphan")
    incidents = relationship("Incident", back_populates="monitor", cascade="all, delete-orphan")
    alert_rules = relationship("AlertRule", back_populates="monitor", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("idx_monitor_workspace_active", "workspace_id", "is_active"),
        Index("idx_monitor_next_check", "next_check_at", "is_active"),
        Index("idx_monitor_status", "current_status"),
        Index("idx_monitor_tags", "tags", postgresql_using="gin"),
    )

    def __repr__(self) -> str:
        return f"<Monitor {self.name} ({self.monitor_type.value})>"


class MonitorCheck(Base):
    """Individual check result (time-series data)"""

    __tablename__ = "monitor_checks"

    # Override id to use BigInteger for better performance with time-series
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    monitor_id = Column(
        UUID(as_uuid=True), ForeignKey("monitors.id", ondelete="CASCADE"), nullable=False
    )
    checked_at = Column(DateTime(timezone=True), nullable=False, index=True)
    region = Column(String(50), nullable=False)

    # Check Result
    status = Column(String(20), nullable=False)  # up, down, timeout, error
    status_code = Column(Integer)
    response_time_ms = Column(Integer)

    # Size Metrics
    response_size_bytes = Column(Integer)

    # Detailed Timing Breakdown
    dns_lookup_time_ms = Column(Integer)
    tcp_connection_time_ms = Column(Integer)
    tls_handshake_time_ms = Column(Integer)
    first_byte_time_ms = Column(Integer)
    content_transfer_time_ms = Column(Integer)

    # Response Details (limited storage for performance)
    response_headers = Column(JSON)
    response_body_sample = Column(Text)  # First 1KB
    response_body_hash = Column(String(64))  # SHA256 for change detection

    # SSL Information
    ssl_valid = Column(Boolean)
    ssl_issuer = Column(String(255))
    ssl_expiry_date = Column(Date)
    ssl_days_remaining = Column(Integer)

    # Error Details
    error_type = Column(String(50))
    error_message = Column(Text)

    # Metadata
    triggered_by = Column(String(50), default="scheduled")  # scheduled, manual, api

    # Relationships
    monitor = relationship("Monitor", back_populates="checks")

    # Indexes for TimescaleDB
    __table_args__ = (
        Index("idx_check_monitor_time", "monitor_id", "checked_at"),
        Index("idx_check_status_time", "status", "checked_at"),
        Index("idx_check_region_time", "region", "checked_at"),
    )

    def __repr__(self) -> str:
        return f"<MonitorCheck {self.monitor_id} at {self.checked_at} - {self.status}>"
