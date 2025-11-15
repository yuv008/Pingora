"""
Incident detection and management tasks
Handles incident creation, updates, and resolution
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional
import structlog
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.workers.celery_app import celery_app
from app.database import AsyncSessionLocal
from app.models.monitor import Monitor, MonitorCheck, MonitorStatus
from app.models.incident import Incident, IncidentStatus, IncidentSeverity, IncidentUpdate
from app.workers.alert_tasks import dispatch_incident_alert

logger = structlog.get_logger()


async def detect_and_create_incident(
    monitor_id: str,
    check_id: str,
    db: AsyncSession
) -> Optional[Incident]:
    """
    Detect and create an incident when a monitor goes down

    Args:
        monitor_id: Monitor UUID
        check_id: MonitorCheck UUID that triggered the incident
        db: Database session

    Returns:
        Incident object if created, None otherwise
    """
    try:
        # Get monitor
        monitor_result = await db.execute(
            select(Monitor).where(Monitor.id == monitor_id)
        )
        monitor = monitor_result.scalar_one_or_none()

        if not monitor:
            return None

        # Check if there's already an ongoing incident for this monitor
        existing_incident = await db.execute(
            select(Incident).where(
                and_(
                    Incident.monitor_id == monitor_id,
                    Incident.status.in_([IncidentStatus.INVESTIGATING, IncidentStatus.IDENTIFIED])
                )
            )
        )
        incident = existing_incident.scalar_one_or_none()

        if incident:
            # Incident already exists, just update it
            logger.info("incident_already_exists", incident_id=str(incident.id))
            return incident

        # Determine severity based on consecutive failures
        if monitor.consecutive_failures >= 5:
            severity = IncidentSeverity.CRITICAL
        elif monitor.consecutive_failures >= 3:
            severity = IncidentSeverity.HIGH
        else:
            severity = IncidentSeverity.MEDIUM

        # Create new incident
        incident = Incident(
            monitor_id=monitor.id,
            workspace_id=monitor.workspace_id,
            title=f"{monitor.name} is down",
            description=f"Monitor '{monitor.name}' has failed {monitor.consecutive_failures} consecutive checks",
            severity=severity,
            status=IncidentStatus.INVESTIGATING,
            started_at=datetime.utcnow(),
            acknowledged_at=None,
            resolved_at=None,
        )

        db.add(incident)

        # Create initial incident update
        update = IncidentUpdate(
            incident_id=incident.id,
            status=IncidentStatus.INVESTIGATING,
            message=f"Monitor started failing at {datetime.utcnow().isoformat()}. Investigating the issue.",
            created_by=None,  # System-generated
        )

        db.add(update)

        await db.commit()
        await db.refresh(incident)

        logger.info(
            "incident_created",
            incident_id=str(incident.id),
            monitor_id=monitor_id,
            severity=severity
        )

        # Dispatch alerts asynchronously
        dispatch_incident_alert.delay(
            incident_id=str(incident.id),
            event_type="created"
        )

        return incident

    except Exception as e:
        logger.error(
            "incident_creation_failed",
            monitor_id=monitor_id,
            error=str(e),
            exc_info=True
        )
        await db.rollback()
        raise


async def resolve_incident(
    monitor_id: str,
    check_id: str,
    db: AsyncSession
) -> Optional[Incident]:
    """
    Resolve an incident when a monitor recovers

    Args:
        monitor_id: Monitor UUID
        check_id: MonitorCheck UUID that resolved the incident
        db: Database session

    Returns:
        Resolved incident object if found, None otherwise
    """
    try:
        # Find ongoing incident for this monitor
        result = await db.execute(
            select(Incident).where(
                and_(
                    Incident.monitor_id == monitor_id,
                    Incident.status.in_([IncidentStatus.INVESTIGATING, IncidentStatus.IDENTIFIED])
                )
            )
        )
        incident = result.scalar_one_or_none()

        if not incident:
            logger.info("no_incident_to_resolve", monitor_id=monitor_id)
            return None

        # Calculate downtime
        downtime_seconds = int((datetime.utcnow() - incident.started_at).total_seconds())

        # Update incident
        incident.status = IncidentStatus.RESOLVED
        incident.resolved_at = datetime.utcnow()

        # Create resolution update
        update = IncidentUpdate(
            incident_id=incident.id,
            status=IncidentStatus.RESOLVED,
            message=f"Monitor has recovered. Total downtime: {downtime_seconds // 60} minutes.",
            created_by=None,  # System-generated
        )

        db.add(update)

        await db.commit()
        await db.refresh(incident)

        logger.info(
            "incident_resolved",
            incident_id=str(incident.id),
            monitor_id=monitor_id,
            downtime_seconds=downtime_seconds
        )

        # Dispatch resolution alerts
        dispatch_incident_alert.delay(
            incident_id=str(incident.id),
            event_type="resolved"
        )

        return incident

    except Exception as e:
        logger.error(
            "incident_resolution_failed",
            monitor_id=monitor_id,
            error=str(e),
            exc_info=True
        )
        await db.rollback()
        raise


@celery_app.task(name="app.workers.incident_tasks.check_ongoing_incidents")
def check_ongoing_incidents():
    """Check ongoing incidents and escalate if needed"""
    return asyncio.run(_check_ongoing_incidents_async())


async def _check_ongoing_incidents_async():
    """Async implementation of checking ongoing incidents"""
    async with AsyncSessionLocal() as db:
        try:
            # Find incidents that have been ongoing for more than 15 minutes
            escalation_threshold = datetime.utcnow() - timedelta(minutes=15)

            result = await db.execute(
                select(Incident).where(
                    and_(
                        Incident.status.in_([IncidentStatus.INVESTIGATING, IncidentStatus.IDENTIFIED]),
                        Incident.started_at < escalation_threshold,
                        Incident.severity != IncidentSeverity.CRITICAL
                    )
                )
            )
            incidents = result.scalars().all()

            escalated_count = 0
            for incident in incidents:
                # Escalate severity
                old_severity = incident.severity

                if incident.severity == IncidentSeverity.LOW:
                    incident.severity = IncidentSeverity.MEDIUM
                elif incident.severity == IncidentSeverity.MEDIUM:
                    incident.severity = IncidentSeverity.HIGH
                elif incident.severity == IncidentSeverity.HIGH:
                    incident.severity = IncidentSeverity.CRITICAL

                # Create escalation update
                update = IncidentUpdate(
                    incident_id=incident.id,
                    status=incident.status,
                    message=f"Incident escalated from {old_severity} to {incident.severity} due to prolonged downtime",
                    created_by=None,
                )

                db.add(update)
                escalated_count += 1

                # Send escalation alert
                dispatch_incident_alert.delay(
                    incident_id=str(incident.id),
                    event_type="escalated"
                )

            await db.commit()

            logger.info("incidents_escalated", count=escalated_count)

            return {"escalated": escalated_count}

        except Exception as e:
            logger.error("incident_check_failed", error=str(e), exc_info=True)
            await db.rollback()
            raise


@celery_app.task(name="app.workers.incident_tasks.acknowledge_incident")
def acknowledge_incident(incident_id: str, acknowledged_by: str):
    """Acknowledge an incident"""
    return asyncio.run(_acknowledge_incident_async(incident_id, acknowledged_by))


async def _acknowledge_incident_async(incident_id: str, acknowledged_by: str):
    """Async implementation of incident acknowledgment"""
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(Incident).where(Incident.id == incident_id)
            )
            incident = result.scalar_one_or_none()

            if not incident:
                return {"error": "Incident not found"}

            incident.acknowledged_at = datetime.utcnow()
            incident.status = IncidentStatus.IDENTIFIED

            # Create acknowledgment update
            update = IncidentUpdate(
                incident_id=incident.id,
                status=IncidentStatus.IDENTIFIED,
                message=f"Incident acknowledged by {acknowledged_by}",
                created_by=acknowledged_by,
            )

            db.add(update)

            await db.commit()

            logger.info("incident_acknowledged", incident_id=incident_id, by=acknowledged_by)

            return {"acknowledged": True, "incident_id": incident_id}

        except Exception as e:
            logger.error("incident_acknowledgment_failed", error=str(e), exc_info=True)
            await db.rollback()
            raise
