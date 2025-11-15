# 🔄 Celery Workers Guide

## Overview

The API Monitor Platform uses Celery for distributed background task execution. This guide explains how the monitoring system works and how to manage the workers.

## Architecture

```
┌─────────────┐
│   FastAPI   │ ─┐
│   Backend   │  │
└─────────────┘  │
                 ├─► ┌───────┐     ┌────────────────┐
┌─────────────┐  │   │ Redis │ ◄───│ Celery Worker  │
│ Celery Beat │ ─┘   │ Broker│     │ (4 processes)  │
│  Scheduler  │      └───────┘     └────────────────┘
└─────────────┘           │
                          │         ┌────────────────┐
                          └────────►│ PostgreSQL +   │
                                    │ TimescaleDB    │
                                    └────────────────┘
```

## Components

### 1. Celery Worker (`celery_worker`)

**Purpose**: Executes monitoring checks and alert dispatching tasks

**Queues**:
- `default` - General tasks
- `monitoring` - Monitor execution tasks (priority: 5)
- `alerts` - Alert dispatching (priority: 9 - highest)
- `incidents` - Incident management (priority: 8)

**Concurrency**: 4 worker processes

**Key Tasks**:
- `execute_monitor_check` - Runs a single monitor check
- `dispatch_incident_alert` - Sends alerts when incidents occur
- `detect_and_create_incident` - Creates incidents on monitor failure

### 2. Celery Beat (`celery_beat`)

**Purpose**: Schedules periodic tasks

**Schedule**:
```python
{
    "queue-due-monitors": {
        "task": "app.workers.monitoring_tasks.queue_due_monitors",
        "schedule": 60.0,  # Every 60 seconds
    },
    "check-stale-monitors": {
        "task": "app.workers.monitoring_tasks.check_stale_monitors",
        "schedule": 300.0,  # Every 5 minutes
    },
    "cleanup-old-checks": {
        "task": "app.workers.monitoring_tasks.cleanup_old_checks",
        "schedule": crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    "update-monitor-stats": {
        "task": "app.workers.monitoring_tasks.update_monitor_statistics",
        "schedule": crontab(minute=0),  # Every hour
    },
    "check-ongoing-incidents": {
        "task": "app.workers.incident_tasks.check_ongoing_incidents",
        "schedule": 60.0,  # Every minute
    },
}
```

### 3. Flower (`flower`)

**Purpose**: Web-based Celery monitoring dashboard

**URL**: http://localhost:5555

**Features**:
- Real-time task monitoring
- Worker status and statistics
- Task history and details
- Queue inspection
- Rate limiting controls

## How Monitoring Works

### Monitor Execution Flow

1. **Queueing Phase** (Every 60 seconds)
   ```
   Celery Beat → queue_due_monitors() → Checks Monitor.next_check_at
                                      → Queues monitors ready for checking
   ```

2. **Execution Phase**
   ```
   Celery Worker → execute_monitor_check(monitor_id)
                 → Fetches monitor from DB
                 → Executes check based on type:
                    - HTTP/HTTPS: aiohttp request
                    - TCP: Socket connection
                    - DNS: DNS resolution
                    - WebSocket: WS handshake
                    - gRPC: Health check
                 → Stores result in monitor_checks table
                 → Updates monitor status
   ```

3. **Incident Detection Phase**
   ```
   If status changed from UP → DOWN:
      → detect_and_create_incident()
      → Create Incident record
      → Create IncidentUpdate
      → Queue alert dispatch

   If status changed from DOWN → UP:
      → resolve_incident()
      → Update Incident (resolved_at)
      → Queue resolution alert
   ```

4. **Alert Dispatching Phase**
   ```
   dispatch_incident_alert(incident_id, event_type)
      → Fetch matching AlertRules
      → Filter by severity, tags, monitors
      → Get AlertChannels
      → Send to each channel:
         - Email (SMTP/SendGrid)
         - Slack (Webhook)
         - Generic Webhook
         - SMS (Twilio)
         - PagerDuty (Events API v2)
      → Log AlertLog record
   ```

## Monitor Types

### HTTP/HTTPS Monitoring

**Check Logic**:
```python
async def _execute_http_check(monitor: Monitor):
    # 1. Make HTTP request with timeout
    # 2. Measure response time
    # 3. Check status code matches expected
    # 4. Verify SSL certificate (HTTPS only)
    # 5. Return status (UP/DOWN/DEGRADED)
```

**Supported Methods**: GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS

**Features**:
- Custom headers
- Request body (POST/PUT/PATCH)
- Expected status codes
- SSL certificate expiry tracking
- Response size tracking

### TCP Monitoring

**Check Logic**:
```python
async def _execute_tcp_check(monitor: Monitor):
    # 1. Parse host:port from URL
    # 2. Attempt TCP connection
    # 3. Measure connection time
    # 4. Return UP if connected, DOWN otherwise
```

**Use Cases**:
- Database servers (PostgreSQL, MySQL, MongoDB)
- Message brokers (RabbitMQ, Redis)
- Custom TCP services

### DNS Monitoring

**Check Logic**:
```python
async def _execute_dns_check(monitor: Monitor):
    # 1. Resolve domain to IP addresses
    # 2. Measure resolution time
    # 3. Return IP addresses in metadata
    # 4. Return UP if resolved, DOWN if NXDOMAIN
```

**Use Cases**:
- Domain availability
- DNS propagation
- Nameserver health

### WebSocket Monitoring

**Check Logic**:
```python
async def _execute_websocket_check(monitor: Monitor):
    # 1. Connect to WebSocket endpoint
    # 2. Send ping frame
    # 3. Measure roundtrip time
    # 4. Close connection
```

**Use Cases**:
- Real-time APIs
- Chat servers
- Live data feeds

### gRPC Monitoring

**Status**: Coming soon

**Planned Features**:
- gRPC health check protocol
- Service reflection
- Custom method calls

## Running Workers Locally

### Start All Services

```bash
docker-compose up -d
```

### Start Only Workers

```bash
# Celery worker
docker-compose up -d celery_worker

# Celery beat
docker-compose up -d celery_beat

# Flower (monitoring)
docker-compose up -d flower
```

### Manual Worker Execution (Development)

```bash
# Terminal 1: Start worker
cd backend
celery -A app.workers.celery_app worker \
    --loglevel=info \
    --concurrency=4 \
    --queues=monitoring,alerts,incidents,default

# Terminal 2: Start beat
celery -A app.workers.celery_app beat \
    --loglevel=info

# Terminal 3: Start Flower
celery -A app.workers.celery_app flower \
    --port=5555
```

## Monitoring & Debugging

### View Worker Logs

```bash
# All workers
docker-compose logs -f celery_worker celery_beat

# Just worker
docker-compose logs -f celery_worker

# Just beat
docker-compose logs -f celery_beat
```

### Access Flower Dashboard

1. Open browser to http://localhost:5555
2. View active tasks, workers, queues
3. Inspect task details and results

### Check Task Status with CLI

```bash
# Inspect active tasks
docker-compose exec celery_worker celery -A app.workers.celery_app inspect active

# Check worker stats
docker-compose exec celery_worker celery -A app.workers.celery_app inspect stats

# View registered tasks
docker-compose exec celery_worker celery -A app.workers.celery_app inspect registered
```

### Debug Individual Tasks

```python
# In Python shell or script
from app.workers.monitoring_tasks import execute_monitor_check

# Execute synchronously for debugging
result = execute_monitor_check(monitor_id="<uuid>", triggered_by="debug")
print(result)
```

## Testing Workers

### Test Monitor Execution

```bash
# 1. Create a test monitor via API
curl -X POST "http://localhost:8000/api/v1/monitors?workspace_id=<workspace_id>" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Monitor",
    "url": "https://httpbin.org/status/200",
    "monitor_type": "https",
    "interval_seconds": 60
  }'

# 2. Trigger manual check
curl -X POST "http://localhost:8000/api/v1/monitors/<monitor_id>/check?workspace_id=<workspace_id>" \
  -H "Authorization: Bearer <token>"

# 3. Check worker logs for execution
docker-compose logs -f celery_worker | grep "monitor_check_completed"

# 4. Verify result in database
docker-compose exec postgres psql -U apimonitor -d apimonitor \
  -c "SELECT * FROM monitor_checks ORDER BY checked_at DESC LIMIT 5;"
```

### Test Incident Creation

```bash
# 1. Create monitor pointing to invalid URL
curl -X POST "http://localhost:8000/api/v1/monitors?workspace_id=<workspace_id>" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Failing Monitor",
    "url": "https://this-domain-definitely-does-not-exist-12345.com",
    "monitor_type": "https",
    "interval_seconds": 60
  }'

# 2. Wait for check to execute (or trigger manually)

# 3. Check for incident creation
curl -X GET "http://localhost:8000/api/v1/incidents?workspace_id=<workspace_id>" \
  -H "Authorization: Bearer <token>"
```

## Performance Tuning

### Worker Concurrency

Adjust based on CPU cores and workload:

```yaml
# docker-compose.yml
command: celery -A app.workers.celery_app worker \
    --loglevel=info \
    --concurrency=8  # Increase for more parallel tasks
```

### Queue Priorities

Ensure critical alerts process first:

```python
# In celery_app.py
task_routes = {
    "app.workers.monitoring_tasks.*": {"queue": "monitoring", "priority": 5},
    "app.workers.alert_tasks.*": {"queue": "alerts", "priority": 9},
}
```

### Task Rate Limiting

Prevent overwhelming external services:

```python
@celery_app.task(rate_limit="100/m")  # 100 tasks per minute
def execute_monitor_check(monitor_id: str):
    ...
```

## Troubleshooting

### Issue: Tasks Not Executing

**Check**:
1. Worker is running: `docker-compose ps celery_worker`
2. Redis is accessible: `docker-compose exec celery_worker redis-cli -h redis ping`
3. Tasks are queued: Check Flower or `celery inspect active`

### Issue: Beat Not Scheduling

**Check**:
1. Beat is running: `docker-compose ps celery_beat`
2. Beat schedule is loaded: Check logs for "beat_schedule"
3. Redis connection is healthy

### Issue: Monitor Not Checking

**Check**:
1. Monitor `is_paused` is False
2. Monitor `next_check_at` is in the past
3. Worker logs show task execution
4. Database connection is healthy

### Issue: Alerts Not Sending

**Check**:
1. Alert channels are enabled
2. Alert rules match the incident
3. Channel credentials are correct
4. Worker logs show alert dispatch attempts

## Production Considerations

### Scaling Workers

```bash
# Run multiple worker instances
docker-compose up -d --scale celery_worker=4
```

### Monitoring

- Set up Sentry for error tracking
- Configure Prometheus metrics
- Use Grafana dashboards
- Enable CloudWatch/DataDog integration

### High Availability

- Run multiple beat schedulers with leader election
- Use Redis Sentinel for failover
- Implement task deduplication
- Set up worker health checks

### Security

- Use SSL/TLS for Redis connections
- Rotate credentials regularly
- Limit worker network access
- Enable task signature verification

## Next Steps

1. ✅ Workers are implemented and ready
2. ⏳ Configure alert channels (Email, Slack, etc.)
3. ⏳ Set up production monitoring
4. ⏳ Implement multi-region workers
5. ⏳ Add worker auto-scaling

---

**Last Updated**: 2025-11-15
**Worker Status**: ✅ Fully Implemented and Operational
