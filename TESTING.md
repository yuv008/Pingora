# 🧪 API Monitor Platform - Testing Guide

## Quick Test (30 seconds)

```bash
# 1. Start the platform
docker-compose up -d

# 2. Wait for services to be ready (10 seconds)
sleep 10

# 3. Run migrations
docker-compose exec backend alembic upgrade head

# 4. Run the API test script
./scripts/test_api.sh
```

Expected output: All 11 tests pass ✅

---

## Manual Testing with curl

### 1. Register a User

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "password": "SecurePass123!",
    "full_name": "Test User"
  }' | jq '.'
```

Save the `access_token` from the response.

### 2. Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123!"
  }' | jq '.'
```

### 3. Get Current User

```bash
TOKEN="your-access-token-here"

curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN" | jq '.'
```

### 4. List Workspaces

```bash
curl -X GET http://localhost:8000/api/v1/workspaces \
  -H "Authorization: Bearer $TOKEN" | jq '.'
```

Save the `workspace_id` from the first workspace.

### 5. Create a Monitor

```bash
WORKSPACE_ID="workspace-id-here"

curl -X POST "http://localhost:8000/api/v1/monitors?workspace_id=$WORKSPACE_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Google Monitor",
    "url": "https://www.google.com",
    "monitor_type": "https",
    "interval_seconds": 300,
    "expected_status_codes": [200]
  }' | jq '.'
```

### 6. List Monitors

```bash
curl -X GET "http://localhost:8000/api/v1/monitors?workspace_id=$WORKSPACE_ID" \
  -H "Authorization: Bearer $TOKEN" | jq '.'
```

---

## Testing with Python

```python
import requests

BASE_URL = "http://localhost:8000/api/v1"

# Register
response = requests.post(f"{BASE_URL}/auth/register", json={
    "email": "python@example.com",
    "username": "pythonuser",
    "password": "SecurePass123!",
    "full_name": "Python User"
})

data = response.json()
token = data["access_token"]

# Get current user
response = requests.get(
    f"{BASE_URL}/auth/me",
    headers={"Authorization": f"Bearer {token}"}
)
print(response.json())

# List workspaces
response = requests.get(
    f"{BASE_URL}/workspaces",
    headers={"Authorization": f"Bearer {token}"}
)
workspaces = response.json()
workspace_id = workspaces[0]["id"]

# Create monitor
response = requests.post(
    f"{BASE_URL}/monitors",
    params={"workspace_id": workspace_id},
    headers={"Authorization": f"Bearer {token}"},
    json={
        "name": "Test Monitor",
        "url": "https://httpbin.org/status/200",
        "monitor_type": "https",
        "interval_seconds": 300
    }
)
print(response.json())
```

---

## Testing with Postman

1. Import the API documentation from http://localhost:8000/api/docs
2. Create an environment with:
   - `base_url`: http://localhost:8000/api/v1
   - `access_token`: (will be set after login)
   - `workspace_id`: (will be set after listing workspaces)

3. Test sequence:
   - POST `/auth/register` → Save `access_token`
   - GET `/auth/me` → Verify user
   - GET `/workspaces` → Save first `workspace_id`
   - POST `/monitors` → Create monitor
   - GET `/monitors` → List monitors

---

## Automated Tests with pytest

```bash
# Run all tests
docker-compose exec backend pytest -v

# Run specific test file
docker-compose exec backend pytest tests/test_api_integration.py -v

# Run with coverage
docker-compose exec backend pytest --cov=app tests/
```

---

## Database Inspection

```bash
# Connect to database
docker-compose exec postgres psql -U apimonitor -d apimonitor

# Check tables
\dt

# Count users
SELECT COUNT(*) FROM users;

# List monitors
SELECT id, name, url, current_status FROM monitors;

# Check recent checks
SELECT * FROM monitor_checks ORDER BY checked_at DESC LIMIT 10;
```

---

## Common Issues & Solutions

### Issue: "Connection refused"

**Solution**: Make sure services are running
```bash
docker-compose ps
# If not running:
docker-compose up -d
```

### Issue: "Table does not exist"

**Solution**: Run migrations
```bash
docker-compose exec backend alembic upgrade head
```

### Issue: "Invalid token"

**Solution**: Register/login again to get a fresh token. Tokens expire after 30 minutes.

### Issue: "Workspace not found"

**Solution**: Make sure you're using the correct `workspace_id` from the workspaces list.

---

## Performance Testing

```bash
# Install Apache Bench
sudo apt-get install apache2-utils

# Test register endpoint (100 requests, 10 concurrent)
ab -n 100 -c 10 -T 'application/json' \
  -p register.json \
  http://localhost:8000/api/v1/auth/register

# Test authenticated endpoint
# First get a token, then:
ab -n 100 -c 10 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/auth/me
```

---

## Load Testing with Locust

Create `locustfile.py`:

```python
from locust import HttpUser, task, between

class APIUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        # Register and login
        response = self.client.post("/api/v1/auth/register", json={
            "email": f"user{self.environment.runner.user_count}@example.com",
            "username": f"user{self.environment.runner.user_count}",
            "password": "SecurePass123!"
        })
        self.token = response.json()["access_token"]
        self.workspace_id = response.json()["user"]["id"]

    @task
    def get_me(self):
        self.client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {self.token}"}
        )

    @task
    def list_monitors(self):
        self.client.get(
            f"/api/v1/monitors?workspace_id={self.workspace_id}",
            headers={"Authorization": f"Bearer {self.token}"}
        )
```

Run:
```bash
locust -f locustfile.py --host=http://localhost:8000
```

---

## Next Steps

After verifying the API works:

1. ✅ Test authentication flow
2. ✅ Test workspace creation
3. ✅ Test monitor CRUD operations
4. ⏳ Implement Celery workers
5. ⏳ Test actual monitoring
6. ⏳ Build frontend
7. ⏳ End-to-end testing

---

**Last Updated**: 2025-11-15
**Status**: Backend API complete and ready for testing
