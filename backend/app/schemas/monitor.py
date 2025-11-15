"""Pydantic schemas for Monitor model"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl, field_validator
from app.models.monitor import MonitorType, MonitorStatus


# Request Schemas
class MonitorCreate(BaseModel):
    """Schema for creating a monitor"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    monitor_type: MonitorType = MonitorType.HTTPS
    url: str = Field(..., min_length=1)
    method: str = Field(default="GET", pattern=r'^(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)$')
    headers: Optional[Dict[str, str]] = None
    body: Optional[str] = None
    interval_seconds: int = Field(default=300, ge=60, le=3600)
    timeout_seconds: int = Field(default=30, ge=5, le=120)
    regions: List[str] = Field(default=["us-east-1"])
    expected_status_codes: List[int] = Field(default=[200])
    tags: Optional[List[str]] = None


class MonitorUpdate(BaseModel):
    """Schema for updating a monitor"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    url: Optional[str] = None
    method: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    interval_seconds: Optional[int] = Field(None, ge=60, le=3600)
    is_active: Optional[bool] = None
    is_paused: Optional[bool] = None


# Response Schemas
class MonitorResponse(BaseModel):
    """Schema for monitor response"""
    id: str
    workspace_id: str
    name: str
    description: Optional[str]
    monitor_type: MonitorType
    url: str
    method: str
    interval_seconds: int
    timeout_seconds: int
    regions: List[str]
    current_status: MonitorStatus
    is_active: bool
    is_paused: bool
    last_checked_at: Optional[datetime]
    uptime_percentage_24h: Optional[float]
    avg_response_time_24h: Optional[float]
    created_at: datetime

    model_config = {"from_attributes": True}


class MonitorCheckResponse(BaseModel):
    """Schema for check result"""
    id: int
    monitor_id: str
    checked_at: datetime
    region: str
    status: str
    status_code: Optional[int]
    response_time_ms: Optional[int]
    error_message: Optional[str]

    model_config = {"from_attributes": True}


class MonitorStatsResponse(BaseModel):
    """Schema for monitor statistics"""
    total_checks: int
    successful_checks: int
    uptime_percentage: float
    avg_response_time: float
    p95_response_time: Optional[float]
    p99_response_time: Optional[float]
