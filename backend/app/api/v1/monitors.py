"""
Monitor endpoints
Manages API monitors and check results
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, text
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_async_session
from app.models.monitor import Monitor, MonitorCheck, MonitorStatus
from app.models.workspace import Workspace
from app.schemas.monitor import (
    MonitorCreate, MonitorUpdate, MonitorResponse,
    MonitorCheckResponse, MonitorStatsResponse
)
from app.api.deps import get_workspace_member, check_workspace_limits
from app.models.workspace import WorkspaceMember
import structlog

router = APIRouter()
logger = structlog.get_logger()


@router.post("/", response_model=MonitorResponse, status_code=status.HTTP_201_CREATED)
async def create_monitor(
    monitor_data: MonitorCreate,
    workspace_id: str = Query(...),
    member: WorkspaceMember = Depends(get_workspace_member),
    db: AsyncSession = Depends(get_async_session)
):
    """Create a new monitor"""
    # Check workspace limits
    workspace = await check_workspace_limits(workspace_id, db)

    if workspace.current_monitors_count >= workspace.max_monitors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Monitor limit reached ({workspace.max_monitors}). Please upgrade your plan."
        )

    # Create monitor
    monitor = Monitor(
        workspace_id=workspace_id,
        name=monitor_data.name,
        description=monitor_data.description,
        monitor_type=monitor_data.monitor_type,
        url=monitor_data.url,
        method=monitor_data.method,
        headers=monitor_data.headers or {},
        body=monitor_data.body,
        interval_seconds=monitor_data.interval_seconds,
        timeout_seconds=monitor_data.timeout_seconds,
        regions=monitor_data.regions,
        expected_status_codes=monitor_data.expected_status_codes,
        tags=monitor_data.tags or [],
        next_check_at=datetime.utcnow()
    )

    db.add(monitor)

    # Update workspace counter
    workspace.current_monitors_count += 1

    await db.commit()
    await db.refresh(monitor)

    logger.info("monitor_created", monitor_id=str(monitor.id), workspace_id=workspace_id)

    # TODO: Trigger immediate check
    # from app.workers.monitoring_tasks import execute_monitor_check
    # execute_monitor_check.delay(str(monitor.id))

    return MonitorResponse.model_validate(monitor)


@router.get("/", response_model=List[MonitorResponse])
async def list_monitors(
    workspace_id: str = Query(...),
    status: Optional[str] = None,
    tags: Optional[List[str]] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    member: WorkspaceMember = Depends(get_workspace_member),
    db: AsyncSession = Depends(get_async_session)
):
    """List monitors in workspace"""
    query = select(Monitor).where(Monitor.workspace_id == workspace_id)

    # Apply filters
    if status:
        query = query.where(Monitor.current_status == status)

    if tags:
        # PostgreSQL array overlap
        query = query.where(Monitor.tags.overlap(tags))

    # Order by name
    query = query.order_by(Monitor.name)

    # Pagination
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    monitors = result.scalars().all()

    return [MonitorResponse.model_validate(m) for m in monitors]


@router.get("/{monitor_id}", response_model=MonitorResponse)
async def get_monitor(
    monitor_id: str,
    workspace_id: str = Query(...),
    member: WorkspaceMember = Depends(get_workspace_member),
    db: AsyncSession = Depends(get_async_session)
):
    """Get monitor details"""
    result = await db.execute(
        select(Monitor).where(
            Monitor.id == monitor_id,
            Monitor.workspace_id == workspace_id
        )
    )
    monitor = result.scalar_one_or_none()

    if not monitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitor not found"
        )

    return MonitorResponse.model_validate(monitor)


@router.put("/{monitor_id}", response_model=MonitorResponse)
async def update_monitor(
    monitor_id: str,
    monitor_data: MonitorUpdate,
    workspace_id: str = Query(...),
    member: WorkspaceMember = Depends(get_workspace_member),
    db: AsyncSession = Depends(get_async_session)
):
    """Update monitor"""
    result = await db.execute(
        select(Monitor).where(
            Monitor.id == monitor_id,
            Monitor.workspace_id == workspace_id
        )
    )
    monitor = result.scalar_one_or_none()

    if not monitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitor not found"
        )

    # Update fields
    update_data = monitor_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(monitor, field, value)

    await db.commit()
    await db.refresh(monitor)

    logger.info("monitor_updated", monitor_id=str(monitor.id))

    return MonitorResponse.model_validate(monitor)


@router.delete("/{monitor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_monitor(
    monitor_id: str,
    workspace_id: str = Query(...),
    member: WorkspaceMember = Depends(get_workspace_member),
    db: AsyncSession = Depends(get_async_session)
):
    """Delete monitor"""
    result = await db.execute(
        select(Monitor).where(
            Monitor.id == monitor_id,
            Monitor.workspace_id == workspace_id
        )
    )
    monitor = result.scalar_one_or_none()

    if not monitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitor not found"
        )

    # Update workspace counter
    workspace = await db.get(Workspace, workspace_id)
    if workspace:
        workspace.current_monitors_count -= 1

    await db.delete(monitor)
    await db.commit()

    logger.info("monitor_deleted", monitor_id=str(monitor.id))

    return None


@router.post("/{monitor_id}/pause")
async def pause_monitor(
    monitor_id: str,
    workspace_id: str = Query(...),
    member: WorkspaceMember = Depends(get_workspace_member),
    db: AsyncSession = Depends(get_async_session)
):
    """Pause monitor checks"""
    result = await db.execute(
        select(Monitor).where(
            Monitor.id == monitor_id,
            Monitor.workspace_id == workspace_id
        )
    )
    monitor = result.scalar_one_or_none()

    if not monitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitor not found"
        )

    monitor.is_paused = True
    monitor.current_status = MonitorStatus.PAUSED
    await db.commit()

    return {"message": "Monitor paused"}


@router.post("/{monitor_id}/resume")
async def resume_monitor(
    monitor_id: str,
    workspace_id: str = Query(...),
    member: WorkspaceMember = Depends(get_workspace_member),
    db: AsyncSession = Depends(get_async_session)
):
    """Resume monitor checks"""
    result = await db.execute(
        select(Monitor).where(
            Monitor.id == monitor_id,
            Monitor.workspace_id == workspace_id
        )
    )
    monitor = result.scalar_one_or_none()

    if not monitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitor not found"
        )

    monitor.is_paused = False
    monitor.current_status = MonitorStatus.UNKNOWN
    monitor.next_check_at = datetime.utcnow()
    await db.commit()

    # TODO: Trigger immediate check

    return {"message": "Monitor resumed"}


@router.post("/{monitor_id}/check")
async def trigger_check(
    monitor_id: str,
    workspace_id: str = Query(...),
    member: WorkspaceMember = Depends(get_workspace_member),
    db: AsyncSession = Depends(get_async_session)
):
    """Manually trigger a monitor check"""
    result = await db.execute(
        select(Monitor).where(
            Monitor.id == monitor_id,
            Monitor.workspace_id == workspace_id
        )
    )
    monitor = result.scalar_one_or_none()

    if not monitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitor not found"
        )

    # TODO: Queue check task
    # from app.workers.monitoring_tasks import execute_monitor_check
    # task = execute_monitor_check.delay(str(monitor.id), triggered_by="manual")

    return {"message": "Check triggered", "monitor_id": str(monitor.id)}


@router.get("/{monitor_id}/checks", response_model=List[MonitorCheckResponse])
async def get_monitor_checks(
    monitor_id: str,
    workspace_id: str = Query(...),
    limit: int = Query(100, ge=1, le=1000),
    member: WorkspaceMember = Depends(get_workspace_member),
    db: AsyncSession = Depends(get_async_session)
):
    """Get monitor check history"""
    # Verify monitor belongs to workspace
    monitor_result = await db.execute(
        select(Monitor).where(
            Monitor.id == monitor_id,
            Monitor.workspace_id == workspace_id
        )
    )
    if not monitor_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitor not found"
        )

    # Get recent checks
    result = await db.execute(
        select(MonitorCheck).where(
            MonitorCheck.monitor_id == monitor_id
        ).order_by(MonitorCheck.checked_at.desc()).limit(limit)
    )
    checks = result.scalars().all()

    return [MonitorCheckResponse.model_validate(c) for c in checks]


@router.get("/{monitor_id}/stats", response_model=MonitorStatsResponse)
async def get_monitor_stats(
    monitor_id: str,
    workspace_id: str = Query(...),
    period: str = Query("24h", regex="^(1h|24h|7d|30d)$"),
    member: WorkspaceMember = Depends(get_workspace_member),
    db: AsyncSession = Depends(get_async_session)
):
    """Get monitor statistics"""
    # Verify monitor
    monitor_result = await db.execute(
        select(Monitor).where(
            Monitor.id == monitor_id,
            Monitor.workspace_id == workspace_id
        )
    )
    if not monitor_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitor not found"
        )

    # Calculate time range
    now = datetime.utcnow()
    if period == "1h":
        start_time = now - timedelta(hours=1)
    elif period == "24h":
        start_time = now - timedelta(days=1)
    elif period == "7d":
        start_time = now - timedelta(days=7)
    else:  # 30d
        start_time = now - timedelta(days=30)

    # Get statistics
    stats_query = text("""
        SELECT
            COUNT(*) as total_checks,
            COUNT(*) FILTER (WHERE status = 'up') as successful_checks,
            AVG(response_time_ms) as avg_response_time,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_time_ms) as p95_response_time,
            PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY response_time_ms) as p99_response_time,
            100.0 * COUNT(*) FILTER (WHERE status = 'up') / NULLIF(COUNT(*), 0) as uptime_percentage
        FROM monitor_checks
        WHERE monitor_id = :monitor_id
            AND checked_at >= :start_time
            AND checked_at <= :end_time
    """)

    result = await db.execute(
        stats_query,
        {
            "monitor_id": monitor_id,
            "start_time": start_time,
            "end_time": now
        }
    )

    stats = result.first()

    return MonitorStatsResponse(
        total_checks=stats.total_checks or 0,
        successful_checks=stats.successful_checks or 0,
        uptime_percentage=float(stats.uptime_percentage or 0),
        avg_response_time=float(stats.avg_response_time or 0),
        p95_response_time=float(stats.p95_response_time or 0) if stats.p95_response_time else None,
        p99_response_time=float(stats.p99_response_time or 0) if stats.p99_response_time else None
    )
