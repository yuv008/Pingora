"""
Celery application configuration
Handles distributed task execution for monitoring
"""
from celery import Celery
from celery.schedules import crontab
from kombu import Queue, Exchange

from app.config import settings

# Create Celery app
celery_app = Celery(
    "api_monitor",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.workers.monitoring_tasks",
        "app.workers.alert_tasks",
        "app.workers.incident_tasks",
    ]
)

# Celery configuration
celery_app.conf.update(
    # Time
    timezone="UTC",
    enable_utc=True,

    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max
    task_soft_time_limit=240,  # 4 minutes soft limit
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Result backend
    result_expires=3600,  # 1 hour
    result_persistent=True,

    # Worker settings
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=False,

    # Retry settings
    task_default_max_retries=3,
    task_default_retry_delay=60,  # 1 minute

    # Queue configuration
    task_default_queue="default",
    task_queues=(
        Queue("default", Exchange("default"), routing_key="default"),
        Queue("monitoring", Exchange("monitoring"), routing_key="monitoring"),
        Queue("alerts", Exchange("alerts"), routing_key="alerts", priority=9),
        Queue("incidents", Exchange("incidents"), routing_key="incidents", priority=8),
    ),

    # Routing
    task_routes={
        "app.workers.monitoring_tasks.*": {"queue": "monitoring"},
        "app.workers.alert_tasks.*": {"queue": "alerts"},
        "app.workers.incident_tasks.*": {"queue": "incidents"},
    },

    # Beat schedule for periodic tasks
    beat_schedule={
        # Queue monitors every minute
        "queue-due-monitors": {
            "task": "app.workers.monitoring_tasks.queue_due_monitors",
            "schedule": 60.0,  # Every 60 seconds
        },
        # Check for stale monitors every 5 minutes
        "check-stale-monitors": {
            "task": "app.workers.monitoring_tasks.check_stale_monitors",
            "schedule": 300.0,  # Every 5 minutes
        },
        # Clean up old check results daily at 2 AM
        "cleanup-old-checks": {
            "task": "app.workers.monitoring_tasks.cleanup_old_checks",
            "schedule": crontab(hour=2, minute=0),
        },
        # Update monitor statistics hourly
        "update-monitor-stats": {
            "task": "app.workers.monitoring_tasks.update_monitor_statistics",
            "schedule": crontab(minute=0),  # Every hour at :00
        },
        # Check for ongoing incidents every minute
        "check-ongoing-incidents": {
            "task": "app.workers.incident_tasks.check_ongoing_incidents",
            "schedule": 60.0,
        },
    },

    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)


@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery setup"""
    return f"Request: {self.request!r}"


# Celery signals for logging
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Setup periodic tasks after Celery configuration"""
    import structlog
    logger = structlog.get_logger()
    logger.info("celery_configured", beat_schedule=list(sender.conf.beat_schedule.keys()))


@celery_app.on_after_finalize.connect
def setup_queues(sender, **kwargs):
    """Ensure all queues are declared"""
    import structlog
    logger = structlog.get_logger()
    logger.info("celery_queues_configured", queues=[q.name for q in sender.conf.task_queues])
