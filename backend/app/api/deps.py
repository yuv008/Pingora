"""
API dependencies for authentication and authorization
Used across all API endpoints
"""
from typing import Optional, AsyncGenerator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_async_session
from app.core.security import security
from app.models.user import User, UserSession
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole

# HTTP Bearer token scheme
security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_async_session)
) -> User:
    """
    Get the current authenticated user from JWT token

    Args:
        credentials: HTTP Bearer credentials
        db: Database session

    Returns:
        Current user object

    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # Verify and decode token
    try:
        payload = security.verify_token(token, token_type="access")
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    session_id = payload.get("session_id")

    if not user_id or not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    # Verify session is still active
    session_result = await db.execute(
        select(UserSession).where(
            UserSession.session_token == session_id,
            UserSession.is_active == True
        )
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has been revoked or expired"
        )

    # Get user
    user_result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )

    # Update session last activity
    session.last_activity = datetime.utcnow()
    session.requests_count += 1
    await db.commit()

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current active user (email must be verified)

    Args:
        current_user: Current user from token

    Returns:
        Current user if active and verified

    Raises:
        HTTPException: If user is not verified
    """
    if not current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please verify your email address."
        )

    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current user if they are a superuser

    Args:
        current_user: Current user from token

    Returns:
        Current user if they are a superuser

    Raises:
        HTTPException: If user is not a superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Superuser access required."
        )

    return current_user


async def get_workspace_member(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
) -> WorkspaceMember:
    """
    Get workspace membership for current user

    Args:
        workspace_id: Workspace ID to check
        current_user: Current authenticated user
        db: Database session

    Returns:
        WorkspaceMember object

    Raises:
        HTTPException: If user is not a member of the workspace
    """
    result = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == current_user.id,
            WorkspaceMember.invitation_accepted == True
        )
    )
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this workspace"
        )

    return member


async def get_workspace_admin(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
) -> WorkspaceMember:
    """
    Get workspace membership if user is admin or owner

    Args:
        workspace_id: Workspace ID to check
        current_user: Current authenticated user
        db: Database session

    Returns:
        WorkspaceMember object if user is admin/owner

    Raises:
        HTTPException: If user is not an admin/owner
    """
    result = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == current_user.id,
            WorkspaceMember.invitation_accepted == True,
            WorkspaceMember.role.in_([WorkspaceRole.OWNER, WorkspaceRole.ADMIN])
        )
    )
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or owner permissions required for this workspace"
        )

    return member


async def get_workspace_owner(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
) -> WorkspaceMember:
    """
    Get workspace membership if user is the owner

    Args:
        workspace_id: Workspace ID to check
        current_user: Current authenticated user
        db: Database session

    Returns:
        WorkspaceMember object if user is owner

    Raises:
        HTTPException: If user is not the owner
    """
    result = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == current_user.id,
            WorkspaceMember.invitation_accepted == True,
            WorkspaceMember.role == WorkspaceRole.OWNER
        )
    )
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner permissions required for this workspace"
        )

    return member


async def check_workspace_limits(
    workspace_id: str,
    db: AsyncSession
) -> Workspace:
    """
    Get workspace and check if it's active and not suspended

    Args:
        workspace_id: Workspace ID to check
        db: Database session

    Returns:
        Workspace object

    Raises:
        HTTPException: If workspace is not found, inactive, or suspended
    """
    result = await db.execute(
        select(Workspace).where(Workspace.id == workspace_id)
    )
    workspace = result.scalar_one_or_none()

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )

    if not workspace.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Workspace is not active"
        )

    if workspace.is_suspended:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Workspace is suspended: {workspace.suspension_reason or 'Contact support'}"
        )

    return workspace


from datetime import datetime
