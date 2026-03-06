"""
Authentication endpoints
Handles user registration, login, logout, and token management
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import secrets

from app.database import get_async_session
from app.core.security import security
from app.models.user import User, UserSession
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole, PlanType
from app.schemas.user import (
    UserRegister, UserLogin, UserResponse, TokenResponse,
    RefreshTokenRequest, PasswordReset, PasswordResetConfirm,
    EmailVerification
)
from app.api.deps import get_current_user
from app.config import settings
import structlog

router = APIRouter()
logger = structlog.get_logger()


def generate_slug(name: str) -> str:
    """Generate a unique slug from name"""
    base_slug = name.lower().replace(" ", "-").replace("_", "-")
    # Add random suffix to ensure uniqueness
    return f"{base_slug}-{secrets.token_hex(4)}"


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Register a new user

    - Creates user account
    - Creates default workspace
    - Returns access and refresh tokens
    """
    # Check if email already exists
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Check if username already exists
    result = await db.execute(
        select(User).where(User.username == user_data.username)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    # Validate password strength
    is_valid, error_msg = security.validate_password_strength(user_data.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )

    # Create user
    hashed_password = security.get_password_hash(user_data.password)
    user = User(
        email=user_data.email,
        username=user_data.username,
        password_hash=hashed_password,
        full_name=user_data.full_name,
        email_verified=False  # TODO: Send verification email
    )
    db.add(user)
    await db.flush()  # Get user.id

    # Create default workspace for user
    workspace_slug = generate_slug(user_data.username)
    workspace = Workspace(
        name=f"{user_data.username}'s Workspace",
        slug=workspace_slug,
        plan_type=PlanType.FREE,
        max_monitors=settings.FREE_MAX_MONITORS,
        max_team_members=settings.FREE_MAX_TEAM_MEMBERS,
        check_interval_minimum=settings.FREE_CHECK_INTERVAL_MIN,
        data_retention_days=settings.FREE_DATA_RETENTION_DAYS
    )
    db.add(workspace)
    await db.flush()

    # Add user as workspace owner
    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user.id,
        role=WorkspaceRole.OWNER,
        invitation_accepted=True,
        joined_at=datetime.utcnow()
    )
    db.add(member)

    # Create session
    session_token = security.generate_session_token()
    refresh_token = security.generate_session_token()

    session = UserSession(
        user_id=user.id,
        session_token=session_token,
        refresh_token=refresh_token,
        access_expires_at=datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        refresh_expires_at=datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        last_activity=datetime.utcnow()
    )
    db.add(session)

    await db.commit()
    await db.refresh(user)

    # Generate tokens
    access_token = security.create_access_token(
        user_id=str(user.id),
        session_id=session_token,
        workspace_id=str(workspace.id)
    )

    refresh_token_jwt = security.create_refresh_token(
        user_id=str(user.id),
        session_id=session_token
    )

    logger.info("user_registered", user_id=str(user.id), email=user.email)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_jwt,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user)
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Login user

    - Validates credentials
    - Creates new session
    - Returns access and refresh tokens
    """
    # Get user by email or username
    if credentials.email:
        result = await db.execute(
            select(User).where(User.email == credentials.email)
        )
    else:
        result = await db.execute(
            select(User).where(User.username == credentials.username)
        )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/username or password"
        )

    # Check if account is locked
    if user.locked_until and user.locked_until > datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is locked. Try again later."
        )

    # Verify password
    if not security.verify_password(credentials.password, user.password_hash):
        # Increment failed attempts
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= 5:
            user.locked_until = datetime.utcnow() + timedelta(minutes=30)
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )

    # Reset failed attempts on successful login
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.utcnow()

    # Get user's primary workspace
    workspace_result = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.user_id == user.id,
            WorkspaceMember.role == WorkspaceRole.OWNER
        ).limit(1)
    )
    workspace_member = workspace_result.scalar_one_or_none()
    workspace_id = str(workspace_member.workspace_id) if workspace_member else None

    # Create session
    session_token = security.generate_session_token()

    session = UserSession(
        user_id=user.id,
        session_token=session_token,
        refresh_token=security.generate_session_token(),
        access_expires_at=datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        refresh_expires_at=datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        last_activity=datetime.utcnow()
    )
    db.add(session)

    await db.commit()

    # Generate tokens
    access_token = security.create_access_token(
        user_id=str(user.id),
        session_id=session_token,
        workspace_id=workspace_id
    )

    refresh_token = security.create_refresh_token(
        user_id=str(user.id),
        session_id=session_token
    )

    logger.info("user_logged_in", user_id=str(user.id), email=user.email)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user)
    )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Logout user

    - Revokes current session
    """
    # Revoke all active sessions for this user
    result = await db.execute(
        select(UserSession).where(
            UserSession.user_id == current_user.id,
            UserSession.is_active == True
        )
    )
    sessions = result.scalars().all()

    for session in sessions:
        session.is_active = False
        session.revoked_at = datetime.utcnow()
        session.revoked_reason = "user_logout"

    await db.commit()

    logger.info("user_logged_out", user_id=str(current_user.id))

    return {"message": "Successfully logged out"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Refresh access token

    - Validates refresh token
    - Issues new access token
    """
    try:
        payload = security.verify_token(refresh_data.refresh_token, token_type="refresh")
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    user_id = payload.get("sub")
    session_id = payload.get("session_id")

    # Verify session exists and is active
    result = await db.execute(
        select(UserSession).where(
            UserSession.session_token == session_id,
            UserSession.is_active == True
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session not found or revoked"
        )

    # Get user
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    # Get workspace
    workspace_result = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.user_id == user.id,
            WorkspaceMember.role == WorkspaceRole.OWNER
        ).limit(1)
    )
    workspace_member = workspace_result.scalar_one_or_none()
    workspace_id = str(workspace_member.workspace_id) if workspace_member else None

    # Generate new access token
    access_token = security.create_access_token(
        user_id=str(user.id),
        session_id=session_id,
        workspace_id=workspace_id
    )

    # Update session
    session.last_activity = datetime.utcnow()
    session.access_expires_at = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_data.refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user)
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information"""
    return UserResponse.model_validate(current_user)
