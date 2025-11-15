# 🚀 Quick Start Guide - API Monitor Platform

Get your API monitoring platform up and running in 5 minutes!

## Prerequisites

- Docker & Docker Compose installed
- Git installed
- 8GB RAM minimum
- Ports available: 3000 (frontend), 8000 (backend), 5432 (postgres), 6379 (redis)

---

## 🎯 Fast Track (Using Docker Compose)

### 1. Clone and Navigate

```bash
cd /home/user/Pingora
```

### 2. Create Environment File

```bash
cp .env.example .env
# Edit .env if needed (defaults work for development)
```

### 3. Start All Services

```bash
docker-compose up -d
```

This will start:
- ✅ PostgreSQL with TimescaleDB (port 5432)
- ✅ Redis (port 6379)
- ✅ FastAPI Backend (port 8000)
- ✅ Next.js Frontend (port 3000)
- ✅ Celery Worker (background)
- ✅ Celery Beat (scheduler)
- ✅ Flower (Celery monitoring, port 5555)

### 4. Verify Services

```bash
# Check all services are running
docker-compose ps

# Check backend health
curl http://localhost:8000/health

# Check frontend
open http://localhost:3000
```

### 5. Access the Platform

- **Frontend**: http://localhost:3000
- **Backend API Docs**: http://localhost:8000/api/docs
- **Flower (Celery Monitor)**: http://localhost:5555

---

## 🛠️ Development Setup (Local)

If you prefer running services locally for development:

### Backend Setup

```bash
cd backend

# Install Poetry (if not installed)
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Create .env file
cp ../.env.example .env

# Run database migrations (after PostgreSQL is running)
poetry run alembic upgrade head

# Start FastAPI server
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# In another terminal, start Celery worker
poetry run celery -A app.workers.celery_app worker --loglevel=info

# In another terminal, start Celery beat
poetry run celery -A app.workers.celery_app beat --loglevel=info
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Create .env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
echo "NEXT_PUBLIC_WS_URL=ws://localhost:8000" >> .env.local

# Start development server
npm run dev
```

---

## 📊 What's Included

### Backend (FastAPI)

✅ **Database Models** (SQLAlchemy + Alembic):
- User with session management
- Workspace for multi-tenancy
- Monitor with multi-protocol support
- MonitorCheck for time-series data
- Incident tracking
- Alert channels and rules

✅ **Configuration**:
- Environment-based settings
- PostgreSQL + TimescaleDB ready
- Redis caching and queuing
- Celery for background jobs

### Frontend (Next.js 14)

📦 **Ready to implement**:
- Authentication pages
- Dashboard with 3D visualizations
- Monitor management UI
- Incident timeline
- Alert configuration
- Status pages

---

## 🎨 3D Visualizations

The platform includes designs for:

1. **Animated Network Background**
   - Particle system showing global connectivity
   - Smooth animations using Three.js

2. **Interactive Status Globe**
   - Real-time monitor status by region
   - 3D globe with location markers

3. **3D Response Time Charts**
   - Beautiful 3D bar charts
   - Interactive data visualization

Implementation examples available in `docs/IMPLEMENTATION_GUIDE.md`

---

## 🔄 Next Implementation Steps

### Phase 1: Core Functionality (Week 1-2)

1. **Authentication Endpoints**
   ```bash
   # Create: backend/app/api/v1/auth.py
   # Implement: register, login, logout, refresh token
   ```

2. **Monitor Endpoints**
   ```bash
   # Create: backend/app/api/v1/monitors.py
   # Implement: CRUD operations, trigger checks, get stats
   ```

3. **Celery Monitoring Tasks**
   ```bash
   # Create: backend/app/workers/monitoring_tasks.py
   # Implement: HTTP/TCP/DNS check execution
   ```

### Phase 2: Frontend & UI (Week 3-4)

4. **Next.js Pages**
   ```bash
   cd frontend/src/app
   # Create: (auth)/login, (auth)/register
   # Create: (dashboard)/monitors, (dashboard)/incidents
   ```

5. **3D Components**
   ```bash
   cd frontend/src/components/3d
   # Create: NetworkBackground.tsx, StatusGlobe.tsx
   # Create: ResponseTimeChart3D.tsx
   ```

### Phase 3: Advanced Features (Week 5-6)

6. **Alert System**
   - Multi-channel notifications
   - Email, Slack, Webhook integration
   - Smart alert rules

7. **Status Pages**
   - Public status pages
   - Custom branding
   - Incident updates

---

## 📚 Documentation

- **README.md**: Project overview and features
- **docs/IMPLEMENTATION_GUIDE.md**: Detailed step-by-step guide
- **docs/API.md**: API documentation (to be created)
- **docs/ARCHITECTURE.md**: System architecture (to be created)

---

## 🧪 Testing

### Run Backend Tests

```bash
cd backend
poetry run pytest --cov=app tests/
```

### Run Frontend Tests

```bash
cd frontend
npm run test
npm run test:e2e
```

---

## 🚀 Deployment

### Docker Compose (Production)

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Kubernetes

```bash
kubectl apply -f infrastructure/kubernetes/
```

---

## 💡 Tips & Tricks

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f celery_worker
```

### Database Management

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U apimonitor -d apimonitor

# Run migrations
docker-compose exec backend alembic upgrade head

# Create new migration
docker-compose exec backend alembic revision --autogenerate -m "description"
```

### Celery Monitoring

Visit http://localhost:5555 for Flower dashboard to monitor:
- Active tasks
- Task history
- Worker status
- Queue depth

---

## 🆘 Troubleshooting

### Services won't start

```bash
# Check logs
docker-compose logs

# Restart services
docker-compose down
docker-compose up -d
```

### Database connection errors

```bash
# Ensure PostgreSQL is healthy
docker-compose ps postgres

# Check PostgreSQL logs
docker-compose logs postgres
```

### Port conflicts

```bash
# Check what's using the port
lsof -i :8000  # or :3000, :5432, etc.

# Change port in docker-compose.yml or .env
```

---

## 📞 Support

- **Documentation**: See `docs/` directory
- **Issues**: Check existing issues or create a new one
- **Community**: Join our Discord/Slack (if available)

---

## 🎉 You're Ready!

Your API monitoring platform foundation is set up. Now you can:

1. ✅ Start implementing the backend endpoints
2. ✅ Build the beautiful frontend with 3D visualizations
3. ✅ Set up monitoring for your first API
4. ✅ Configure alerts and notifications
5. ✅ Deploy to production

Happy monitoring! 🚀
