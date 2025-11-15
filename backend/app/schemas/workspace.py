"""Pydantic schemas for Workspace model"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.workspace import PlanType, WorkspaceRole


# Request Schemas
class WorkspaceCreate(BaseModel):
    """Schema for creating a workspace"""
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=3, max_length=100, pattern=r'^[a-z0-9-]+$')
    description: Optional[str] = None


class WorkspaceUpdate(BaseModel):
    """Schema for updating workspace"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class WorkspaceMemberInvite(BaseModel):
    """Schema for inviting a member"""
    email: str = Field(..., description="Email of user to invite")
    role: WorkspaceRole = Field(default=WorkspaceRole.MEMBER)


# Response Schemas
class WorkspaceResponse(BaseModel):
    """Schema for workspace response"""
    id: str
    name: str
    slug: str
    description: Optional[str]
    plan_type: PlanType
    max_monitors: int
    max_team_members: int
    current_monitors_count: int
    current_members_count: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkspaceMemberResponse(BaseModel):
    """Schema for workspace member"""
    id: str
    user_id: str
    workspace_id: str
    role: WorkspaceRole
    joined_at: Optional[datetime]

    model_config = {"from_attributes": True}


class WorkspaceWithMembers(WorkspaceResponse):
    """Workspace with members list"""
    members: List[WorkspaceMemberResponse] = []
