"""
Alert dispatching tasks
Handles sending alerts via Email, Slack, Webhook, SMS, and PagerDuty
"""
import asyncio
from datetime import datetime
from typing import Dict, Any, List
import aiohttp
import structlog
from sqlalchemy import select, and_

from app.workers.celery_app import celery_app
from app.database import AsyncSessionLocal
from app.models.incident import Incident
from app.models.alert import AlertChannel, AlertRule, AlertLog, AlertChannelType, AlertStatus
from app.models.monitor import Monitor
from app.config import settings

logger = structlog.get_logger()


@celery_app.task(name="app.workers.alert_tasks.dispatch_incident_alert")
def dispatch_incident_alert(incident_id: str, event_type: str):
    """
    Dispatch alerts for an incident event

    Args:
        incident_id: Incident UUID
        event_type: Type of event (created, escalated, resolved)
    """
    return asyncio.run(_dispatch_incident_alert_async(incident_id, event_type))


async def _dispatch_incident_alert_async(incident_id: str, event_type: str):
    """Async implementation of alert dispatching"""
    async with AsyncSessionLocal() as db:
        try:
            # Get incident with monitor
            incident_result = await db.execute(
                select(Incident).where(Incident.id == incident_id)
            )
            incident = incident_result.scalar_one_or_none()

            if not incident:
                logger.warning("incident_not_found", incident_id=incident_id)
                return {"error": "Incident not found"}

            # Get monitor
            monitor_result = await db.execute(
                select(Monitor).where(Monitor.id == incident.monitor_id)
            )
            monitor = monitor_result.scalar_one_or_none()

            if not monitor:
                logger.warning("monitor_not_found", monitor_id=str(incident.monitor_id))
                return {"error": "Monitor not found"}

            # Get alert rules for this workspace
            rules_result = await db.execute(
                select(AlertRule).where(
                    and_(
                        AlertRule.workspace_id == incident.workspace_id,
                        AlertRule.is_enabled == True
                    )
                )
            )
            rules = rules_result.scalars().all()

            # Filter rules that match this event
            matching_rules = []
            for rule in rules:
                if _rule_matches_event(rule, incident, monitor, event_type):
                    matching_rules.append(rule)

            if not matching_rules:
                logger.info(
                    "no_matching_alert_rules",
                    incident_id=incident_id,
                    event_type=event_type
                )
                return {"sent": 0, "reason": "No matching rules"}

            # Get alert channels for matching rules
            channel_ids = set()
            for rule in matching_rules:
                channel_ids.update(rule.channel_ids)

            if not channel_ids:
                logger.info("no_alert_channels", incident_id=incident_id)
                return {"sent": 0, "reason": "No channels configured"}

            channels_result = await db.execute(
                select(AlertChannel).where(
                    and_(
                        AlertChannel.id.in_(list(channel_ids)),
                        AlertChannel.is_enabled == True
                    )
                )
            )
            channels = channels_result.scalars().all()

            # Prepare alert payload
            alert_payload = _build_alert_payload(incident, monitor, event_type)

            # Send alerts to each channel
            sent_count = 0
            for channel in channels:
                try:
                    await _send_alert_to_channel(
                        channel=channel,
                        payload=alert_payload,
                        incident=incident,
                        db=db
                    )
                    sent_count += 1
                except Exception as e:
                    logger.error(
                        "alert_send_failed",
                        channel_id=str(channel.id),
                        channel_type=channel.channel_type,
                        error=str(e)
                    )

            logger.info(
                "alerts_dispatched",
                incident_id=incident_id,
                event_type=event_type,
                sent_count=sent_count
            )

            return {"sent": sent_count, "channels": len(channels)}

        except Exception as e:
            logger.error("alert_dispatch_failed", error=str(e), exc_info=True)
            raise


def _rule_matches_event(
    rule: AlertRule,
    incident: Incident,
    monitor: Monitor,
    event_type: str
) -> bool:
    """Check if an alert rule matches the incident event"""
    # Check event type
    if event_type == "created" and not rule.trigger_on_down:
        return False
    if event_type == "resolved" and not rule.trigger_on_recovery:
        return False

    # Check severity
    if rule.min_severity:
        severity_levels = {
            "low": 1,
            "medium": 2,
            "high": 3,
            "critical": 4
        }
        if severity_levels.get(incident.severity, 0) < severity_levels.get(rule.min_severity, 0):
            return False

    # Check monitor filter
    if rule.monitor_ids and str(monitor.id) not in rule.monitor_ids:
        return False

    # Check tags filter
    if rule.monitor_tags:
        if not monitor.tags or not any(tag in monitor.tags for tag in rule.monitor_tags):
            return False

    return True


def _build_alert_payload(incident: Incident, monitor: Monitor, event_type: str) -> Dict[str, Any]:
    """Build alert payload for notification"""
    return {
        "incident_id": str(incident.id),
        "event_type": event_type,
        "title": incident.title,
        "description": incident.description,
        "severity": incident.severity,
        "status": incident.status,
        "monitor": {
            "id": str(monitor.id),
            "name": monitor.name,
            "url": monitor.url,
            "type": monitor.monitor_type,
        },
        "started_at": incident.started_at.isoformat() if incident.started_at else None,
        "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None,
        "downtime_seconds": (
            int((incident.resolved_at - incident.started_at).total_seconds())
            if incident.resolved_at and incident.started_at
            else None
        ),
        "timestamp": datetime.utcnow().isoformat(),
    }


async def _send_alert_to_channel(
    channel: AlertChannel,
    payload: Dict[str, Any],
    incident: Incident,
    db
):
    """Send alert to a specific channel"""
    start_time = datetime.utcnow()

    try:
        if channel.channel_type == AlertChannelType.EMAIL:
            success = await _send_email_alert(channel, payload)
        elif channel.channel_type == AlertChannelType.SLACK:
            success = await _send_slack_alert(channel, payload)
        elif channel.channel_type == AlertChannelType.WEBHOOK:
            success = await _send_webhook_alert(channel, payload)
        elif channel.channel_type == AlertChannelType.SMS:
            success = await _send_sms_alert(channel, payload)
        elif channel.channel_type == AlertChannelType.PAGERDUTY:
            success = await _send_pagerduty_alert(channel, payload)
        else:
            logger.warning("unsupported_channel_type", channel_type=channel.channel_type)
            success = False

        # Log alert
        alert_log = AlertLog(
            workspace_id=incident.workspace_id,
            incident_id=incident.id,
            channel_id=channel.id,
            channel_type=channel.channel_type,
            status=AlertStatus.SENT if success else AlertStatus.FAILED,
            sent_at=datetime.utcnow(),
            delivered_at=datetime.utcnow() if success else None,
            error_message=None if success else "Failed to send alert",
            retry_count=0,
        )

        db.add(alert_log)
        await db.commit()

        return success

    except Exception as e:
        # Log failed alert
        alert_log = AlertLog(
            workspace_id=incident.workspace_id,
            incident_id=incident.id,
            channel_id=channel.id,
            channel_type=channel.channel_type,
            status=AlertStatus.FAILED,
            sent_at=datetime.utcnow(),
            error_message=str(e),
            retry_count=0,
        )

        db.add(alert_log)
        await db.commit()

        raise


async def _send_email_alert(channel: AlertChannel, payload: Dict[str, Any]) -> bool:
    """Send email alert"""
    # TODO: Implement email sending via SMTP or service like SendGrid
    logger.info(
        "email_alert_placeholder",
        to=channel.config.get("recipient"),
        subject=payload["title"]
    )
    return True


async def _send_slack_alert(channel: AlertChannel, payload: Dict[str, Any]) -> bool:
    """Send Slack alert via webhook"""
    try:
        webhook_url = channel.config.get("webhook_url")

        if not webhook_url:
            logger.error("slack_webhook_missing", channel_id=str(channel.id))
            return False

        # Build Slack message
        color = {
            "critical": "#FF0000",
            "high": "#FF6600",
            "medium": "#FFAA00",
            "low": "#FFEE00"
        }.get(payload["severity"], "#808080")

        event_emoji = {
            "created": "🚨",
            "escalated": "⚠️",
            "resolved": "✅"
        }.get(payload["event_type"], "ℹ️")

        slack_message = {
            "text": f"{event_emoji} {payload['title']}",
            "attachments": [
                {
                    "color": color,
                    "fields": [
                        {
                            "title": "Monitor",
                            "value": payload["monitor"]["name"],
                            "short": True
                        },
                        {
                            "title": "Severity",
                            "value": payload["severity"].upper(),
                            "short": True
                        },
                        {
                            "title": "URL",
                            "value": payload["monitor"]["url"],
                            "short": False
                        },
                        {
                            "title": "Status",
                            "value": payload["status"],
                            "short": True
                        },
                    ],
                    "footer": "API Monitor Platform",
                    "ts": int(datetime.utcnow().timestamp())
                }
            ]
        }

        # Add downtime for resolved incidents
        if payload["event_type"] == "resolved" and payload["downtime_seconds"]:
            downtime_minutes = payload["downtime_seconds"] // 60
            slack_message["attachments"][0]["fields"].append({
                "title": "Downtime",
                "value": f"{downtime_minutes} minutes",
                "short": True
            })

        async with aiohttp.ClientSession() as session:
            async with session.post(
                webhook_url,
                json=slack_message,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    logger.info("slack_alert_sent", channel_id=str(channel.id))
                    return True
                else:
                    error_text = await response.text()
                    logger.error(
                        "slack_alert_failed",
                        status=response.status,
                        error=error_text
                    )
                    return False

    except Exception as e:
        logger.error("slack_alert_error", error=str(e), exc_info=True)
        return False


async def _send_webhook_alert(channel: AlertChannel, payload: Dict[str, Any]) -> bool:
    """Send generic webhook alert"""
    try:
        webhook_url = channel.config.get("url")
        headers = channel.config.get("headers", {})

        if not webhook_url:
            logger.error("webhook_url_missing", channel_id=str(channel.id))
            return False

        async with aiohttp.ClientSession() as session:
            async with session.post(
                webhook_url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if 200 <= response.status < 300:
                    logger.info("webhook_alert_sent", channel_id=str(channel.id))
                    return True
                else:
                    error_text = await response.text()
                    logger.error(
                        "webhook_alert_failed",
                        status=response.status,
                        error=error_text
                    )
                    return False

    except Exception as e:
        logger.error("webhook_alert_error", error=str(e), exc_info=True)
        return False


async def _send_sms_alert(channel: AlertChannel, payload: Dict[str, Any]) -> bool:
    """Send SMS alert via Twilio"""
    # TODO: Implement Twilio SMS integration
    logger.info(
        "sms_alert_placeholder",
        to=channel.config.get("phone_number"),
        message=payload["title"]
    )
    return True


async def _send_pagerduty_alert(channel: AlertChannel, payload: Dict[str, Any]) -> bool:
    """Send PagerDuty alert"""
    try:
        integration_key = channel.config.get("integration_key")

        if not integration_key:
            logger.error("pagerduty_key_missing", channel_id=str(channel.id))
            return False

        # Map event type to PagerDuty action
        action = "trigger"
        if payload["event_type"] == "resolved":
            action = "resolve"

        pagerduty_payload = {
            "routing_key": integration_key,
            "event_action": action,
            "dedup_key": f"incident_{payload['incident_id']}",
            "payload": {
                "summary": payload["title"],
                "severity": payload["severity"],
                "source": payload["monitor"]["url"],
                "custom_details": {
                    "monitor_name": payload["monitor"]["name"],
                    "monitor_type": payload["monitor"]["type"],
                    "description": payload["description"],
                }
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://events.pagerduty.com/v2/enqueue",
                json=pagerduty_payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 202:
                    logger.info("pagerduty_alert_sent", channel_id=str(channel.id))
                    return True
                else:
                    error_text = await response.text()
                    logger.error(
                        "pagerduty_alert_failed",
                        status=response.status,
                        error=error_text
                    )
                    return False

    except Exception as e:
        logger.error("pagerduty_alert_error", error=str(e), exc_info=True)
        return False


@celery_app.task(name="app.workers.alert_tasks.retry_failed_alerts")
def retry_failed_alerts():
    """Retry alerts that failed to send"""
    return asyncio.run(_retry_failed_alerts_async())


async def _retry_failed_alerts_async():
    """Async implementation of retrying failed alerts"""
    async with AsyncSessionLocal() as db:
        try:
            # Find failed alerts from the last hour with retry count < 3
            retry_window = datetime.utcnow() - timedelta(hours=1)

            result = await db.execute(
                select(AlertLog).where(
                    and_(
                        AlertLog.status == AlertStatus.FAILED,
                        AlertLog.sent_at >= retry_window,
                        AlertLog.retry_count < 3
                    )
                )
            )
            failed_alerts = result.scalars().all()

            retried_count = 0
            for alert_log in failed_alerts:
                # Re-dispatch the alert
                dispatch_incident_alert.delay(
                    incident_id=str(alert_log.incident_id),
                    event_type="retry"
                )

                # Increment retry count
                alert_log.retry_count += 1
                retried_count += 1

            await db.commit()

            logger.info("failed_alerts_retried", count=retried_count)

            return {"retried": retried_count}

        except Exception as e:
            logger.error("alert_retry_failed", error=str(e), exc_info=True)
            await db.rollback()
            raise
