# 🚀 API Monitor Platform - Complete Implementation Guide

This guide provides step-by-step instructions to complete the implementation of the API Monitoring SaaS platform with 3D visualizations.

## 📋 Table of Contents

1. [Backend Implementation](#backend-implementation)
2. [Frontend Implementation](#frontend-implementation)
3. [3D Visualizations](#3d-visualizations)
4. [Testing](#testing)
5. [Deployment](#deployment)

---

## 🔧 Backend Implementation

### Phase 1: Authentication & Security

#### 1.1 Create Security Module (`backend/app/core/security.py`)

```python
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from app.config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
```

#### 1.2 Create API Dependencies (`backend/app/api/deps.py`)

```python
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_async_session
from app.core.security import verify_token
from app.models import User, WorkspaceMember

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_async_session)
) -> User:
    token = credentials.credentials
    payload = verify_token(token)
    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return user

async def get_current_workspace_member(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
) -> WorkspaceMember:
    result = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == current_user.id
        )
    )
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    return member
```

### Phase 2: API Endpoints

#### 2.1 Authentication Endpoints (`backend/app/api/v1/auth.py`)

Create registration, login, logout, password reset, and token refresh endpoints.

#### 2.2 Monitor Endpoints (`backend/app/api/v1/monitors.py`)

- `POST /monitors` - Create monitor
- `GET /monitors` - List monitors with filters
- `GET /monitors/{id}` - Get monitor details
- `PUT /monitors/{id}` - Update monitor
- `DELETE /monitors/{id}` - Delete monitor
- `POST /monitors/{id}/check` - Trigger manual check
- `GET /monitors/{id}/checks` - Get check history
- `GET /monitors/{id}/stats` - Get statistics

#### 2.3 Incident Endpoints (`backend/app/api/v1/incidents.py`)

- `GET /incidents` - List incidents
- `GET /incidents/{id}` - Get incident details
- `POST /incidents/{id}/acknowledge` - Acknowledge incident
- `POST /incidents/{id}/resolve` - Resolve incident
- `POST /incidents/{id}/updates` - Add incident update

#### 2.4 Alert Endpoints (`backend/app/api/v1/alerts.py`)

- `POST /alert-channels` - Create alert channel
- `GET /alert-channels` - List alert channels
- `POST /alert-rules` - Create alert rule
- `GET /alert-logs` - Get alert history

### Phase 3: Celery Workers

#### 3.1 Celery Configuration (`backend/app/workers/celery_app.py`)

```python
from celery import Celery
from celery.schedules import crontab
from app.config import settings

celery_app = Celery(
    "api_monitor",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    beat_schedule={
        'check-monitors': {
            'task': 'app.workers.monitoring_tasks.check_all_monitors',
            'schedule': 60.0,  # Every minute
        },
    }
)
```

#### 3.2 Monitoring Tasks (`backend/app/workers/monitoring_tasks.py`)

```python
import httpx
from celery import shared_task
from app.models import Monitor, MonitorCheck
from app.database import get_sync_session

@shared_task
def execute_monitor_check(monitor_id: str, region: str = "us-east-1"):
    with get_sync_session() as db:
        monitor = db.query(Monitor).filter(Monitor.id == monitor_id).first()
        if not monitor:
            return

        # Execute HTTP check
        start_time = time.time()
        try:
            response = httpx.get(
                monitor.url,
                headers=monitor.headers,
                timeout=monitor.timeout_seconds
            )
            response_time = int((time.time() - start_time) * 1000)

            # Create check record
            check = MonitorCheck(
                monitor_id=monitor.id,
                checked_at=datetime.utcnow(),
                region=region,
                status="up" if response.status_code in monitor.expected_status_codes else "down",
                status_code=response.status_code,
                response_time_ms=response_time
            )
            db.add(check)
            db.commit()
        except Exception as e:
            check = MonitorCheck(
                monitor_id=monitor.id,
                checked_at=datetime.utcnow(),
                region=region,
                status="error",
                error_message=str(e)
            )
            db.add(check)
            db.commit()
```

### Phase 4: FastAPI Main Application

#### 4.1 Create Main App (`backend/app/main.py`)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import api_router
from app.config import settings
from app.database import init_db

app = FastAPI(
    title="API Monitor Platform",
    version="1.0.0",
    docs_url="/api/docs" if settings.ENVIRONMENT != "production" else None
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

@app.on_event("startup")
async def startup():
    await init_db()

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

---

## 💻 Frontend Implementation

### Phase 1: Next.js Setup

#### 1.1 Initialize Next.js Project

```bash
cd frontend
npx create-next-app@latest . --typescript --tailwind --app --import-alias "@/*"
```

#### 1.2 Install Dependencies

```bash
npm install @tanstack/react-query axios zustand react-hook-form @hookform/resolvers zod
npm install recharts date-fns socket.io-client react-hot-toast
npm install three @react-three/fiber @react-three/drei
npm install @radix-ui/react-dialog @radix-ui/react-dropdown-menu @radix-ui/react-select
npm install lucide-react class-variance-authority clsx tailwind-merge
```

#### 1.3 Create Package.json (`frontend/package.json`)

```json
{
  "name": "api-monitor-frontend",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "test": "jest",
    "test:e2e": "playwright test"
  },
  "dependencies": {
    "next": "14.1.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "@tanstack/react-query": "^5.17.0",
    "axios": "^1.6.5",
    "zustand": "^4.4.7",
    "react-hook-form": "^7.48.2",
    "@hookform/resolvers": "^3.3.4",
    "zod": "^3.22.4",
    "recharts": "^2.10.4",
    "date-fns": "^3.2.0",
    "socket.io-client": "^4.5.4",
    "react-hot-toast": "^2.4.1",
    "three": "^0.160.0",
    "@react-three/fiber": "^8.15.0",
    "@react-three/drei": "^9.93.0",
    "@radix-ui/react-alert-dialog": "^1.0.5",
    "@radix-ui/react-dialog": "^1.0.5",
    "@radix-ui/react-dropdown-menu": "^2.0.6",
    "@radix-ui/react-select": "^2.0.0",
    "lucide-react": "^0.309.0",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.2.0"
  },
  "devDependencies": {
    "@types/node": "^20",
    "@types/react": "^18",
    "@types/react-dom": "^18",
    "@types/three": "^0.160.0",
    "typescript": "^5",
    "eslint": "^8",
    "eslint-config-next": "14.1.0",
    "tailwindcss": "^3.3.0",
    "postcss": "^8",
    "autoprefixer": "^10.0.1"
  }
}
```

### Phase 2: API Client & State Management

#### 2.1 Create API Client (`frontend/src/lib/api.ts`)

```typescript
import axios from 'axios';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for adding auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const authAPI = {
  login: (email: string, password: string) =>
    api.post('/api/v1/auth/login', { email, password }),
  register: (data: any) =>
    api.post('/api/v1/auth/register', data),
  logout: () =>
    api.post('/api/v1/auth/logout'),
};

export const monitorsAPI = {
  list: (params?: any) =>
    api.get('/api/v1/monitors', { params }),
  create: (data: any) =>
    api.post('/api/v1/monitors', data),
  get: (id: string) =>
    api.get(`/api/v1/monitors/${id}`),
  update: (id: string, data: any) =>
    api.put(`/api/v1/monitors/${id}`, data),
  delete: (id: string) =>
    api.delete(`/api/v1/monitors/${id}`),
  trigger: (id: string) =>
    api.post(`/api/v1/monitors/${id}/check`),
};

export default api;
```

---

## 🎨 3D Visualizations Implementation

### Phase 1: 3D Landing Page

#### 1.1 Animated Network Background (`frontend/src/components/3d/NetworkBackground.tsx`)

```typescript
'use client';

import { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Points, PointMaterial } from '@react-three/drei';
import * as THREE from 'three';

function NetworkParticles() {
  const ref = useRef<THREE.Points>(null);

  const particles = useMemo(() => {
    const count = 1000;
    const positions = new Float32Array(count * 3);

    for (let i = 0; i < count; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 10;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 10;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 10;
    }

    return positions;
  }, []);

  useFrame((state) => {
    if (ref.current) {
      ref.current.rotation.x = state.clock.elapsedTime * 0.1;
      ref.current.rotation.y = state.clock.elapsedTime * 0.15;
    }
  });

  return (
    <Points ref={ref} positions={particles} stride={3} frustumCulled={false}>
      <PointMaterial
        transparent
        color="#3b82f6"
        size={0.02}
        sizeAttenuation={true}
        depthWrite={false}
      />
    </Points>
  );
}

export default function NetworkBackground() {
  return (
    <div className="fixed inset-0 -z-10">
      <Canvas camera={{ position: [0, 0, 5] }}>
        <ambientLight intensity={0.5} />
        <NetworkParticles />
      </Canvas>
    </div>
  );
}
```

### Phase 2: 3D Status Globe

#### 2.1 Interactive Globe with Monitoring Locations (`frontend/src/components/3d/StatusGlobe.tsx`)

```typescript
'use client';

import { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Sphere, MeshDistortMaterial, OrbitControls } from '@react-three/drei';
import * as THREE from 'three';

interface MonitorLocation {
  lat: number;
  lon: number;
  status: 'up' | 'down' | 'degraded';
  name: string;
}

function Globe({ locations }: { locations: MonitorLocation[] }) {
  const globeRef = useRef<THREE.Mesh>(null);

  useFrame(() => {
    if (globeRef.current) {
      globeRef.current.rotation.y += 0.001;
    }
  });

  return (
    <group>
      <Sphere ref={globeRef} args={[2, 64, 64]}>
        <MeshDistortMaterial
          color="#0ea5e9"
          attach="material"
          distort={0.1}
          speed={1.5}
          roughness={0.4}
        />
      </Sphere>

      {locations.map((location, index) => {
        const phi = (90 - location.lat) * (Math.PI / 180);
        const theta = (location.lon + 180) * (Math.PI / 180);

        const x = -2 * Math.sin(phi) * Math.cos(theta);
        const y = 2 * Math.cos(phi);
        const z = 2 * Math.sin(phi) * Math.sin(theta);

        const color = {
          up: '#22c55e',
          down: '#ef4444',
          degraded: '#f59e0b'
        }[location.status];

        return (
          <mesh key={index} position={[x, y, z]}>
            <sphereGeometry args={[0.05, 16, 16]} />
            <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.5} />
          </mesh>
        );
      })}
    </group>
  );
}

export default function StatusGlobe({ locations }: { locations: MonitorLocation[] }) {
  return (
    <Canvas camera={{ position: [0, 0, 6] }}>
      <ambientLight intensity={0.5} />
      <pointLight position={[10, 10, 10]} />
      <Globe locations={locations} />
      <OrbitControls enableZoom={false} enablePan={false} />
    </Canvas>
  );
}
```

### Phase 3: 3D Charts

#### 3.1 3D Response Time Chart (`frontend/src/components/3d/ResponseTimeChart3D.tsx`)

```typescript
'use client';

import { useMemo } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import * as THREE from 'three';

interface DataPoint {
  timestamp: string;
  value: number;
}

function Chart3D({ data }: { data: DataPoint[] }) {
  const bars = useMemo(() => {
    const maxValue = Math.max(...data.map(d => d.value));

    return data.map((point, index) => {
      const height = (point.value / maxValue) * 3;
      const x = (index - data.length / 2) * 0.2;

      return {
        position: [x, height / 2, 0] as [number, number, number],
        scale: [0.15, height, 0.15] as [number, number, number],
        color: point.value > maxValue * 0.7 ? '#ef4444' : '#22c55e'
      };
    });
  }, [data]);

  return (
    <group>
      {bars.map((bar, index) => (
        <mesh key={index} position={bar.position}>
          <boxGeometry args={bar.scale} />
          <meshStandardMaterial color={bar.color} />
        </mesh>
      ))}
    </group>
  );
}

export default function ResponseTimeChart3D({ data }: { data: DataPoint[] }) {
  return (
    <div className="h-96 w-full">
      <Canvas camera={{ position: [5, 5, 5] }}>
        <ambientLight intensity={0.5} />
        <pointLight position={[10, 10, 10]} />
        <Chart3D data={data} />
        <OrbitControls />
        <gridHelper args={[10, 10]} />
      </Canvas>
    </div>
  );
}
```

---

## 🧪 Testing Implementation

### Backend Tests (`backend/tests/test_auth.py`)

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_register_user():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "SecurePass123!",
                "full_name": "Test User"
            }
        )
        assert response.status_code == 201
        assert "id" in response.json()
```

### Frontend Tests (`frontend/__tests__/api.test.ts`)

```typescript
import { monitorsAPI } from '@/lib/api';

describe('Monitors API', () => {
  it('should list monitors', async () => {
    const response = await monitorsAPI.list();
    expect(response.status).toBe(200);
    expect(Array.isArray(response.data)).toBe(true);
  });
});
```

---

## 🚀 Deployment

### Docker Compose Production

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Kubernetes Deployment

Create manifests in `infrastructure/kubernetes/`:
- `deployment.yaml`
- `service.yaml`
- `ingress.yaml`
- `configmap.yaml`
- `secrets.yaml`

---

## 📝 Next Steps

1. ✅ Complete FastAPI endpoints implementation
2. ✅ Implement Celery monitoring workers
3. ✅ Build Next.js pages and components
4. ✅ Add 3D visualization components
5. ✅ Implement WebSocket for real-time updates
6. ✅ Add Stripe billing integration
7. ✅ Write comprehensive tests
8. ✅ Set up CI/CD pipeline
9. ✅ Deploy to production

---

## 🎯 Priority Features

**Week 1-2:**
- Authentication system
- Monitor CRUD operations
- Basic monitoring execution
- Simple dashboard

**Week 3-4:**
- Alert channels and rules
- Incident management
- Email notifications
- 3D landing page

**Week 5-6:**
- Advanced 3D visualizations
- Status pages
- Team management
- Stripe integration

**Week 7-8:**
- Performance optimization
- Testing
- Documentation
- Production deployment
