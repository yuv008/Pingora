# 🚀 Deployment Guide

Complete guide for deploying the API Monitor Platform to production.

## Table of Contents

1. [Quick Start (Docker)](#quick-start-docker)
2. [Production Deployment](#production-deployment)
3. [Environment Variables](#environment-variables)
4. [Database Setup](#database-setup)
5. [Monitoring & Logging](#monitoring--logging)
6. [Scaling](#scaling)
7. [Security](#security)
8. [Troubleshooting](#troubleshooting)

## Quick Start (Docker)

### Local Development

```bash
# Clone the repository
git clone <repository-url>
cd Pingora

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Access services:
# - Frontend: http://localhost:3000
# - Backend API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
# - Flower (Celery): http://localhost:5555
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3001
```

### Run Database Migrations

```bash
# Enter backend container
docker-compose exec backend bash

# Run migrations
alembic upgrade head

# Exit container
exit
```

### Create Test User

```bash
# Use the test script
./scripts/test_api.sh

# Or via API
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "username": "admin",
    "password": "SecurePassword123!",
    "full_name": "Admin User"
  }'
```

## Production Deployment

### Requirements

- **Docker** 24.0+ and Docker Compose 2.0+
- **PostgreSQL** 15+ with TimescaleDB extension
- **Redis** 7.0+
- **Node.js** 18+ (for frontend build)
- **Python** 3.11+
- **SSL Certificates** (Let's Encrypt recommended)

### 1. Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install docker-compose-plugin

# Create application directory
sudo mkdir -p /opt/api-monitor
sudo chown $USER:$USER /opt/api-monitor
cd /opt/api-monitor

# Clone repository
git clone <repository-url> .
```

### 2. Environment Configuration

```bash
# Create production environment file
cp .env.example .env.production

# Edit environment variables
nano .env.production
```

**Critical Environment Variables:**

```env
# Application
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=<generate-strong-64-char-secret>
JWT_SECRET_KEY=<generate-strong-64-char-secret>

# Database
DATABASE_URL=postgresql+asyncpg://apimonitor:STRONG_PASSWORD@postgres:5432/apimonitor
DATABASE_URL_SYNC=postgresql://apimonitor:STRONG_PASSWORD@postgres:5432/apimonitor

# Redis
REDIS_URL=redis://:STRONG_PASSWORD@redis:6379/0

# Celery
CELERY_BROKER_URL=redis://:STRONG_PASSWORD@redis:6379/0
CELERY_RESULT_BACKEND=redis://:STRONG_PASSWORD@redis:6379/0

# CORS (Frontend domain)
BACKEND_CORS_ORIGINS=["https://monitor.yourdomain.com"]

# Email (for alerts)
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=<sendgrid-api-key>
SMTP_FROM_EMAIL=noreply@yourdomain.com

# Stripe (for billing)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Monitoring
SENTRY_DSN=https://...@sentry.io/...
```

### 3. SSL Certificates

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Generate certificates
sudo certbot certonly --standalone -d api.yourdomain.com -d monitor.yourdomain.com

# Certificates will be in:
# /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem
# /etc/letsencrypt/live/api.yourdomain.com/privkey.pem
```

### 4. Production Docker Compose

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: timescale/timescaledb:latest-pg15
    restart: always
    environment:
      POSTGRES_DB: apimonitor
      POSTGRES_USER: apimonitor
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_HOST_AUTH_METHOD: scram-sha-256
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - internal

  redis:
    image: redis:7-alpine
    restart: always
    command: redis-server --requirepass ${REDIS_PASSWORD} --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - internal

  backend:
    build:
      context: ./backend
      dockerfile: ../infrastructure/docker/backend.Dockerfile
      target: production
    restart: always
    env_file: .env.production
    volumes:
      - backend_logs:/app/logs
    networks:
      - internal
      - web
    depends_on:
      - postgres
      - redis

  celery_worker:
    build:
      context: ./backend
      dockerfile: ../infrastructure/docker/backend.Dockerfile
      target: production
    restart: always
    env_file: .env.production
    command: celery -A app.workers.celery_app worker --loglevel=info --concurrency=8
    volumes:
      - celery_logs:/app/logs
    networks:
      - internal
    depends_on:
      - postgres
      - redis

  celery_beat:
    build:
      context: ./backend
      dockerfile: ../infrastructure/docker/backend.Dockerfile
      target: production
    restart: always
    env_file: .env.production
    command: celery -A app.workers.celery_app beat --loglevel=info
    networks:
      - internal
    depends_on:
      - postgres
      - redis

  frontend:
    build:
      context: ./frontend
      dockerfile: ../infrastructure/docker/frontend.Dockerfile
      target: production
    restart: always
    environment:
      - NEXT_PUBLIC_API_URL=https://api.yourdomain.com
      - NEXT_PUBLIC_WS_URL=wss://api.yourdomain.com
    networks:
      - web

  nginx:
    image: nginx:alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./infrastructure/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro
      - nginx_logs:/var/log/nginx
    networks:
      - web
    depends_on:
      - backend
      - frontend

volumes:
  postgres_data:
  redis_data:
  backend_logs:
  celery_logs:
  nginx_logs:

networks:
  internal:
    driver: bridge
  web:
    driver: bridge
```

### 5. Nginx Configuration

Create `infrastructure/nginx/nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream backend {
        server backend:8000;
    }

    upstream frontend {
        server frontend:3000;
    }

    # Backend API
    server {
        listen 443 ssl http2;
        server_name api.yourdomain.com;

        ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;

        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        client_max_body_size 10M;

        location / {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }

    # Frontend
    server {
        listen 443 ssl http2;
        server_name monitor.yourdomain.com;

        ssl_certificate /etc/letsencrypt/live/monitor.yourdomain.com/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/monitor.yourdomain.com/privkey.pem;

        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }

    # HTTP to HTTPS redirect
    server {
        listen 80;
        server_name api.yourdomain.com monitor.yourdomain.com;
        return 301 https://$server_name$request_uri;
    }
}
```

### 6. Deploy

```bash
# Build and start services
docker-compose -f docker-compose.prod.yml up -d --build

# Run database migrations
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Check logs
docker-compose -f docker-compose.prod.yml logs -f

# Verify services
curl https://api.yourdomain.com/health
curl https://monitor.yourdomain.com
```

## Environment Variables

### Backend Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| ENVIRONMENT | Yes | development | Environment name |
| DEBUG | No | true | Enable debug mode |
| SECRET_KEY | Yes | - | App secret key (64+ chars) |
| JWT_SECRET_KEY | Yes | - | JWT secret (64+ chars) |
| DATABASE_URL | Yes | - | PostgreSQL connection URL |
| REDIS_URL | Yes | - | Redis connection URL |
| BACKEND_CORS_ORIGINS | Yes | ["*"] | Allowed CORS origins |
| SMTP_HOST | No | - | SMTP server host |
| SMTP_PORT | No | 587 | SMTP server port |
| SENTRY_DSN | No | - | Sentry error tracking |

### Frontend Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| NEXT_PUBLIC_API_URL | Yes | http://localhost:8000 | Backend API URL |
| NEXT_PUBLIC_WS_URL | Yes | ws://localhost:8000 | WebSocket URL |
| NEXT_PUBLIC_APP_URL | Yes | http://localhost:3000 | Frontend URL |

## Database Setup

### Initial Setup

```sql
-- Connect to PostgreSQL
psql -U postgres

-- Create database and user
CREATE DATABASE apimonitor;
CREATE USER apimonitor WITH ENCRYPTED PASSWORD 'your-password';
GRANT ALL PRIVILEGES ON DATABASE apimonitor TO apimonitor;

-- Enable TimescaleDB
\c apimonitor
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Verify
SELECT * FROM pg_extension WHERE extname = 'timescaledb';
```

### Backup & Restore

```bash
# Backup
docker-compose exec postgres pg_dump -U apimonitor apimonitor > backup.sql

# Restore
docker-compose exec -T postgres psql -U apimonitor apimonitor < backup.sql

# Automated backups (add to crontab)
0 2 * * * /opt/api-monitor/scripts/backup-db.sh
```

## Monitoring & Logging

### Application Monitoring

**Sentry Integration:**
```python
# Already configured in app/main.py
sentry_sdk.init(dsn=settings.SENTRY_DSN)
```

**Prometheus Metrics:**
- Endpoint: `http://localhost:8000/metrics`
- Grafana Dashboard: Import `infrastructure/grafana/dashboard.json`

### Log Aggregation

```bash
# View all logs
docker-compose logs -f

# View specific service
docker-compose logs -f backend
docker-compose logs -f celery_worker

# Export logs
docker-compose logs --no-color > logs.txt
```

### Health Checks

```bash
# Backend health
curl http://localhost:8000/health

# Database health
docker-compose exec postgres pg_isready

# Redis health
docker-compose exec redis redis-cli ping

# Celery health (via Flower)
curl http://localhost:5555/api/workers
```

## Scaling

### Horizontal Scaling

**Add More Celery Workers:**
```bash
docker-compose -f docker-compose.prod.yml up -d --scale celery_worker=4
```

**Load Balancing (Multiple Backend Instances):**
```yaml
# docker-compose.prod.yml
services:
  backend:
    deploy:
      replicas: 3
```

### Database Optimization

```sql
-- Add indexes for common queries
CREATE INDEX idx_monitors_workspace_status ON monitors(workspace_id, current_status);
CREATE INDEX idx_monitor_checks_monitor_time ON monitor_checks(monitor_id, checked_at DESC);
CREATE INDEX idx_incidents_workspace_status ON incidents(workspace_id, status);

-- Vacuum and analyze
VACUUM ANALYZE;

-- Monitor query performance
SELECT * FROM pg_stat_statements ORDER BY total_exec_time DESC LIMIT 10;
```

### Redis Configuration

```conf
# redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
```

## Security

### Security Checklist

- [ ] Change all default passwords
- [ ] Use strong SECRET_KEY and JWT_SECRET_KEY (64+ characters)
- [ ] Enable HTTPS with valid SSL certificates
- [ ] Configure CORS to only allow your frontend domain
- [ ] Set up firewall rules (only allow 80, 443, 22)
- [ ] Enable Redis password authentication
- [ ] Use environment variables for secrets (never commit)
- [ ] Enable database SSL connections
- [ ] Set up regular backups
- [ ] Configure rate limiting
- [ ] Enable Sentry error tracking
- [ ] Review and update dependencies regularly
- [ ] Set up monitoring and alerts
- [ ] Use non-root containers
- [ ] Enable audit logging

### Firewall Configuration

```bash
# UFW firewall rules
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
sudo ufw status
```

## Troubleshooting

### Common Issues

**1. Database Connection Error**
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check logs
docker-compose logs postgres

# Verify connection
docker-compose exec postgres psql -U apimonitor -c "SELECT version();"
```

**2. Celery Workers Not Processing**
```bash
# Check Celery worker status
docker-compose logs celery_worker

# Inspect queues
docker-compose exec backend celery -A app.workers.celery_app inspect active

# Purge queues (development only!)
docker-compose exec backend celery -A app.workers.celery_app purge
```

**3. Frontend Can't Connect to Backend**
```bash
# Check CORS settings in backend/.env
BACKEND_CORS_ORIGINS=["http://localhost:3000"]

# Verify API is accessible
curl http://localhost:8000/api/v1/health

# Check browser console for CORS errors
```

**4. Out of Memory**
```bash
# Check memory usage
docker stats

# Increase Celery concurrency
# In docker-compose.yml: --concurrency=2

# Add memory limits
services:
  celery_worker:
    deploy:
      resources:
        limits:
          memory: 1G
```

### Performance Issues

**Slow API Responses:**
```bash
# Enable query logging
# In backend/.env: DATABASE_ECHO=true

# Check slow queries
SELECT * FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

# Add database indexes
# See Database Optimization section
```

**High CPU Usage:**
```bash
# Monitor processes
docker-compose top

# Reduce Celery worker concurrency
# In docker-compose.yml: --concurrency=2

# Profile Python code
pip install py-spy
py-spy record -o profile.svg -- python app/main.py
```

## Additional Resources

- [Backend API Documentation](http://localhost:8000/docs)
- [Celery Workers Guide](WORKERS_GUIDE.md)
- [Testing Guide](TESTING.md)
- [Frontend Progress](FRONTEND_PROGRESS.md)
- [Docker Documentation](https://docs.docker.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [TimescaleDB Documentation](https://docs.timescale.com/)

---

**Need Help?** Open an issue on GitHub or contact the development team.
