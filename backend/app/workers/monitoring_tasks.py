"""
Monitoring tasks for executing checks across different protocols
Handles HTTP/HTTPS, TCP, DNS, WebSocket, and gRPC monitoring
"""
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import aiohttp
import dns.resolver
import structlog
from celery import Task
from sqlalchemy import select, and_, or_, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.workers.celery_app import celery_app
from app.database import AsyncSessionLocal
from app.models.monitor import Monitor, MonitorCheck, MonitorStatus, MonitorType
from app.models.incident import Incident, IncidentStatus, IncidentSeverity
from app.workers.incident_tasks import detect_and_create_incident, resolve_incident

logger = structlog.get_logger()


class MonitoringTask(Task):
    """Base task class with database session management"""
    _session = None

    @property
    def session(self):
        if self._session is None:
            self._session = AsyncSessionLocal()
        return self._session

    def after_return(self, *args, **kwargs):
        if self._session is not None:
            asyncio.run(self._session.close())
            self._session = None


@celery_app.task(base=MonitoringTask, name="app.workers.monitoring_tasks.execute_monitor_check")
def execute_monitor_check(monitor_id: str, triggered_by: str = "scheduled"):
    """
    Execute a monitor check

    Args:
        monitor_id: Monitor UUID
        triggered_by: Source of trigger (scheduled, manual, recovery)
    """
    return asyncio.run(_execute_monitor_check_async(monitor_id, triggered_by))


async def _execute_monitor_check_async(monitor_id: str, triggered_by: str):
    """Async implementation of monitor check execution"""
    async with AsyncSessionLocal() as db:
        try:
            # Get monitor
            result = await db.execute(
                select(Monitor).where(Monitor.id == monitor_id)
            )
            monitor = result.scalar_one_or_none()

            if not monitor:
                logger.warning("monitor_not_found", monitor_id=monitor_id)
                return {"error": "Monitor not found"}

            if monitor.is_paused:
                logger.info("monitor_paused", monitor_id=monitor_id)
                return {"skipped": "Monitor is paused"}

            # Execute check based on monitor type
            start_time = time.time()
            check_result = await _execute_check_by_type(monitor)
            execution_time = int((time.time() - start_time) * 1000)  # ms

            # Store check result
            check = MonitorCheck(
                monitor_id=monitor.id,
                region=check_result.get("region", "default"),
                status=check_result["status"],
                response_time_ms=check_result.get("response_time_ms", execution_time),
                status_code=check_result.get("status_code"),
                error_message=check_result.get("error_message"),
                checked_at=datetime.utcnow(),
                ssl_expiry_days=check_result.get("ssl_expiry_days"),
                response_size_bytes=check_result.get("response_size_bytes"),
                metadata=check_result.get("metadata", {})
            )

            db.add(check)

            # Update monitor status
            previous_status = monitor.current_status
            monitor.current_status = check_result["status"]
            monitor.last_check_at = datetime.utcnow()
            monitor.last_check_duration_ms = check.response_time_ms

            if check_result["status"] == MonitorStatus.UP:
                monitor.last_success_at = datetime.utcnow()
                monitor.consecutive_failures = 0
                monitor.consecutive_successes += 1

                # Calculate uptime percentage (last 24 hours)
                uptime_stats = await _calculate_uptime(db, monitor.id, hours=24)
                monitor.uptime_percentage = uptime_stats["uptime_percentage"]

            else:
                monitor.last_failure_at = datetime.utcnow()
                monitor.consecutive_failures += 1
                monitor.consecutive_successes = 0

            # Update next check time
            monitor.next_check_at = datetime.utcnow() + timedelta(seconds=monitor.interval_seconds)

            await db.commit()

            # Check for incidents (status changes)
            if previous_status != check_result["status"]:
                if check_result["status"] == MonitorStatus.DOWN:
                    # Monitor went down - detect incident
                    await detect_and_create_incident(
                        monitor_id=monitor.id,
                        check_id=check.id,
                        db=db
                    )
                elif check_result["status"] == MonitorStatus.UP and previous_status == MonitorStatus.DOWN:
                    # Monitor recovered - resolve incident
                    await resolve_incident(
                        monitor_id=monitor.id,
                        check_id=check.id,
                        db=db
                    )

            logger.info(
                "monitor_check_completed",
                monitor_id=monitor_id,
                status=check_result["status"],
                response_time=check.response_time_ms,
                triggered_by=triggered_by
            )

            return {
                "monitor_id": str(monitor.id),
                "status": check_result["status"],
                "response_time_ms": check.response_time_ms,
                "checked_at": check.checked_at.isoformat()
            }

        except Exception as e:
            logger.error(
                "monitor_check_failed",
                monitor_id=monitor_id,
                error=str(e),
                exc_info=True
            )
            await db.rollback()
            raise


async def _execute_check_by_type(monitor: Monitor) -> Dict[str, Any]:
    """Execute check based on monitor type"""
    if monitor.monitor_type in [MonitorType.HTTP, MonitorType.HTTPS]:
        return await _execute_http_check(monitor)
    elif monitor.monitor_type == MonitorType.TCP:
        return await _execute_tcp_check(monitor)
    elif monitor.monitor_type == MonitorType.DNS:
        return await _execute_dns_check(monitor)
    elif monitor.monitor_type == MonitorType.WEBSOCKET:
        return await _execute_websocket_check(monitor)
    elif monitor.monitor_type == MonitorType.GRPC:
        return await _execute_grpc_check(monitor)
    else:
        return {
            "status": MonitorStatus.UNKNOWN,
            "error_message": f"Unsupported monitor type: {monitor.monitor_type}"
        }


async def _execute_http_check(monitor: Monitor) -> Dict[str, Any]:
    """Execute HTTP/HTTPS check"""
    try:
        timeout = aiohttp.ClientTimeout(total=monitor.timeout_seconds)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            start_time = time.time()

            async with session.request(
                method=monitor.method,
                url=monitor.url,
                headers=monitor.headers or {},
                data=monitor.body if monitor.method in ["POST", "PUT", "PATCH"] else None,
                ssl=True,  # Verify SSL by default
                allow_redirects=True
            ) as response:
                response_time = int((time.time() - start_time) * 1000)
                response_text = await response.text()

                # Check if status code is expected
                expected_codes = monitor.expected_status_codes or [200]
                is_status_ok = response.status in expected_codes

                # Determine status
                if is_status_ok:
                    status = MonitorStatus.UP
                    error_message = None
                else:
                    status = MonitorStatus.DOWN
                    error_message = f"Unexpected status code: {response.status}"

                # Get SSL expiry if HTTPS
                ssl_expiry_days = None
                if monitor.monitor_type == MonitorType.HTTPS:
                    # TODO: Parse SSL certificate expiry
                    pass

                return {
                    "status": status,
                    "response_time_ms": response_time,
                    "status_code": response.status,
                    "error_message": error_message,
                    "ssl_expiry_days": ssl_expiry_days,
                    "response_size_bytes": len(response_text),
                    "metadata": {
                        "content_type": response.headers.get("Content-Type"),
                        "server": response.headers.get("Server"),
                    }
                }

    except asyncio.TimeoutError:
        return {
            "status": MonitorStatus.DOWN,
            "error_message": f"Request timeout after {monitor.timeout_seconds}s",
            "response_time_ms": monitor.timeout_seconds * 1000
        }
    except aiohttp.ClientError as e:
        return {
            "status": MonitorStatus.DOWN,
            "error_message": f"Connection error: {str(e)}",
        }
    except Exception as e:
        return {
            "status": MonitorStatus.DOWN,
            "error_message": f"Check failed: {str(e)}",
        }


async def _execute_tcp_check(monitor: Monitor) -> Dict[str, Any]:
    """Execute TCP port check"""
    try:
        # Parse host and port from URL
        import urllib.parse
        parsed = urllib.parse.urlparse(monitor.url)
        host = parsed.hostname or parsed.path.split(":")[0]
        port = parsed.port or int(parsed.path.split(":")[-1])

        start_time = time.time()

        # Attempt TCP connection
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=monitor.timeout_seconds
        )

        response_time = int((time.time() - start_time) * 1000)
        writer.close()
        await writer.wait_closed()

        return {
            "status": MonitorStatus.UP,
            "response_time_ms": response_time,
            "metadata": {"host": host, "port": port}
        }

    except asyncio.TimeoutError:
        return {
            "status": MonitorStatus.DOWN,
            "error_message": f"Connection timeout after {monitor.timeout_seconds}s",
        }
    except Exception as e:
        return {
            "status": MonitorStatus.DOWN,
            "error_message": f"TCP connection failed: {str(e)}",
        }


async def _execute_dns_check(monitor: Monitor) -> Dict[str, Any]:
    """Execute DNS resolution check"""
    try:
        # Parse domain from URL
        import urllib.parse
        parsed = urllib.parse.urlparse(monitor.url)
        domain = parsed.hostname or parsed.path

        start_time = time.time()

        # Resolve DNS
        resolver = dns.resolver.Resolver()
        resolver.timeout = monitor.timeout_seconds
        resolver.lifetime = monitor.timeout_seconds

        answers = resolver.resolve(domain, 'A')
        response_time = int((time.time() - start_time) * 1000)

        ip_addresses = [str(rdata) for rdata in answers]

        return {
            "status": MonitorStatus.UP,
            "response_time_ms": response_time,
            "metadata": {
                "domain": domain,
                "ip_addresses": ip_addresses,
                "record_count": len(ip_addresses)
            }
        }

    except dns.resolver.NXDOMAIN:
        return {
            "status": MonitorStatus.DOWN,
            "error_message": "Domain does not exist (NXDOMAIN)",
        }
    except dns.resolver.Timeout:
        return {
            "status": MonitorStatus.DOWN,
            "error_message": f"DNS query timeout after {monitor.timeout_seconds}s",
        }
    except Exception as e:
        return {
            "status": MonitorStatus.DOWN,
            "error_message": f"DNS resolution failed: {str(e)}",
        }


async def _execute_websocket_check(monitor: Monitor) -> Dict[str, Any]:
    """Execute WebSocket check"""
    try:
        import aiohttp

        start_time = time.time()
        timeout = aiohttp.ClientTimeout(total=monitor.timeout_seconds)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.ws_connect(monitor.url) as ws:
                # Send ping
                await ws.ping()
                response_time = int((time.time() - start_time) * 1000)

                await ws.close()

        return {
            "status": MonitorStatus.UP,
            "response_time_ms": response_time,
        }

    except asyncio.TimeoutError:
        return {
            "status": MonitorStatus.DOWN,
            "error_message": f"WebSocket timeout after {monitor.timeout_seconds}s",
        }
    except Exception as e:
        return {
            "status": MonitorStatus.DOWN,
            "error_message": f"WebSocket connection failed: {str(e)}",
        }


async def _execute_grpc_check(monitor: Monitor) -> Dict[str, Any]:
    """Execute gRPC health check"""
    # TODO: Implement gRPC health check
    # Requires grpcio and grpc-health-checking packages
    return {
        "status": MonitorStatus.UNKNOWN,
        "error_message": "gRPC monitoring not yet implemented"
    }


async def _calculate_uptime(db: AsyncSession, monitor_id: str, hours: int = 24) -> Dict[str, Any]:
    """Calculate uptime percentage for a monitor"""
    start_time = datetime.utcnow() - timedelta(hours=hours)

    query = text("""
        SELECT
            COUNT(*) as total_checks,
            COUNT(*) FILTER (WHERE status = 'up') as successful_checks,
            100.0 * COUNT(*) FILTER (WHERE status = 'up') / NULLIF(COUNT(*), 0) as uptime_percentage
        FROM monitor_checks
        WHERE monitor_id = :monitor_id
            AND checked_at >= :start_time
    """)

    result = await db.execute(
        query,
        {"monitor_id": monitor_id, "start_time": start_time}
    )

    stats = result.first()

    return {
        "total_checks": stats.total_checks or 0,
        "successful_checks": stats.successful_checks or 0,
        "uptime_percentage": float(stats.uptime_percentage or 100.0)
    }


@celery_app.task(name="app.workers.monitoring_tasks.queue_due_monitors")
def queue_due_monitors():
    """Queue all monitors that are due for checking"""
    return asyncio.run(_queue_due_monitors_async())


async def _queue_due_monitors_async():
    """Async implementation of queueing due monitors"""
    async with AsyncSessionLocal() as db:
        try:
            now = datetime.utcnow()

            # Find monitors due for checking
            result = await db.execute(
                select(Monitor).where(
                    and_(
                        Monitor.is_paused == False,
                        Monitor.next_check_at <= now
                    )
                )
            )
            monitors = result.scalars().all()

            queued_count = 0
            for monitor in monitors:
                # Queue the check task
                execute_monitor_check.delay(str(monitor.id), triggered_by="scheduled")
                queued_count += 1

            logger.info("monitors_queued", count=queued_count)

            return {"queued": queued_count, "timestamp": now.isoformat()}

        except Exception as e:
            logger.error("queue_monitors_failed", error=str(e), exc_info=True)
            raise


@celery_app.task(name="app.workers.monitoring_tasks.check_stale_monitors")
def check_stale_monitors():
    """Check for monitors that haven't been checked in a while"""
    return asyncio.run(_check_stale_monitors_async())


async def _check_stale_monitors_async():
    """Async implementation of checking stale monitors"""
    async with AsyncSessionLocal() as db:
        try:
            # Find monitors that should have been checked but weren't
            stale_threshold = datetime.utcnow() - timedelta(minutes=10)

            result = await db.execute(
                select(Monitor).where(
                    and_(
                        Monitor.is_paused == False,
                        or_(
                            Monitor.last_check_at == None,
                            Monitor.last_check_at < stale_threshold
                        )
                    )
                )
            )
            stale_monitors = result.scalars().all()

            recovered_count = 0
            for monitor in stale_monitors:
                # Force immediate check
                monitor.next_check_at = datetime.utcnow()
                execute_monitor_check.delay(str(monitor.id), triggered_by="recovery")
                recovered_count += 1

            await db.commit()

            logger.info("stale_monitors_recovered", count=recovered_count)

            return {"recovered": recovered_count}

        except Exception as e:
            logger.error("stale_check_failed", error=str(e), exc_info=True)
            await db.rollback()
            raise


@celery_app.task(name="app.workers.monitoring_tasks.cleanup_old_checks")
def cleanup_old_checks():
    """Clean up old check results (already handled by TimescaleDB retention)"""
    # TimescaleDB retention policy handles this automatically
    # This task is a placeholder for manual cleanup if needed
    logger.info("cleanup_old_checks_skipped", reason="Handled by TimescaleDB retention policy")
    return {"skipped": True}


@celery_app.task(name="app.workers.monitoring_tasks.update_monitor_statistics")
def update_monitor_statistics():
    """Update cached statistics for all monitors"""
    return asyncio.run(_update_monitor_statistics_async())


async def _update_monitor_statistics_async():
    """Async implementation of updating monitor statistics"""
    async with AsyncSessionLocal() as db:
        try:
            # Get all active monitors
            result = await db.execute(select(Monitor))
            monitors = result.scalars().all()

            updated_count = 0
            for monitor in monitors:
                # Calculate 24h uptime
                uptime_stats = await _calculate_uptime(db, monitor.id, hours=24)
                monitor.uptime_percentage = uptime_stats["uptime_percentage"]
                updated_count += 1

            await db.commit()

            logger.info("monitor_statistics_updated", count=updated_count)

            return {"updated": updated_count}

        except Exception as e:
            logger.error("statistics_update_failed", error=str(e), exc_info=True)
            await db.rollback()
            raise
