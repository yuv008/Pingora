"""
Workspace endpoints
Manages workspaces and team members
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_async_session
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.schemas.workspace import (
    WorkspaceCreate, WorkspaceUpdate, WorkspaceResponse,
    WorkspaceMemberResponse, WorkspaceWithMembers
)
from app.api.deps import get_current_user, get_workspace_member, get_workspace_owner
import structlog

router = APIRouter()
logger = structlog.get_logger()


@router.post("/", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    workspace_data: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Create a new workspace"""
    # Check if slug is already taken
    result = await db.execute(
        select(Workspace).where(Workspace.slug == workspace_data.slug)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workspace slug already taken"
        )

    # Create workspace
    workspace = Workspace(
        name=workspace_data.name,
        slug=workspace_data.slug,
        description=workspace_data.description
    )
    db.add(workspace)
    await db.flush()

    # Add current user as owner
    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=current_user.id,
        role=WorkspaceRole.OWNER,
        invitation_accepted=True
    )
    db.add(member)

    await db.commit()
    await db.refresh(workspace)

    logger.info("workspace_created", workspace_id=str(workspace.id), user_id=str(current_user.id))

    return WorkspaceResponse.model_validate(workspace)


@router.get("/", response_model=List[WorkspaceResponse])
async def list_workspaces(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """List all workspaces user is a member of"""
    result = await db.execute(
        select(Workspace).join(WorkspaceMember).where(
            WorkspaceMember.user_id == current_user.id,
            WorkspaceMember.invitation_accepted == True
        )
    )
    workspaces = result.scalars().all()

    return [WorkspaceResponse.model_validate(ws) for ws in workspaces]


@router.get("/{workspace_id}", response_model=WorkspaceWithMembers)
async def get_workspace(
    workspace_id: str,
    member: WorkspaceMember = Depends(get_workspace_member),
    db: AsyncSession = Depends(get_async_session)
):
    """Get workspace details"""
    result = await db.execute(
        select(Workspace).where(Workspace.id == workspace_id)
    )
    workspace = result.scalar_one_or_none()

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )

    # Get members
    members_result = await db.execute(
        select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace_id)
    )
    members = members_result.scalars().all()

    response = WorkspaceWithMembers.model_validate(workspace)
    response.members = [WorkspaceMemberResponse.model_validate(m) for m in members]

    return response


@router.put("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: str,
    workspace_data: WorkspaceUpdate,
    owner: WorkspaceMember = Depends(get_workspace_owner),
    db: AsyncSession = Depends(get_async_session)
):
    """Update workspace (owner only)"""
    result = await db.execute(
        select(Workspace).where(Workspace.id == workspace_id)
    )
    workspace = result.scalar_one_or_none()

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )

    # Update fields
    if workspace_data.name is not None:
        workspace.name = workspace_data.name
    if workspace_data.description is not None:
        workspace.description = workspace_data.description

    await db.commit()
    await db.refresh(workspace)

    logger.info("workspace_updated", workspace_id=str(workspace.id))

    return WorkspaceResponse.model_validate(workspace)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: str,
    owner: WorkspaceMember = Depends(get_workspace_owner),
    db: AsyncSession = Depends(get_async_session)
):
    """Delete workspace (owner only)"""
    result = await db.execute(
        select(Workspace).where(Workspace.id == workspace_id)
    )
    workspace = result.scalar_one_or_none()

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )

    await db.delete(workspace)
    await db.commit()

    logger.info("workspace_deleted", workspace_id=str(workspace.id))

    return None
