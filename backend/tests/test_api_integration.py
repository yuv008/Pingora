"""
Integration tests for API endpoints
Tests the complete user flow: register -> login -> create monitor
"""
import pytest
from httpx import AsyncClient
from app.main import app
import asyncio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_user_registration():
    """Test user registration"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "username": "testuser",
                "password": "SecurePass123!",
                "full_name": "Test User"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == "test@example.com"


@pytest.mark.anyio
async def test_user_login():
    """Test user login"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # First register
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "login@example.com",
                "username": "loginuser",
                "password": "SecurePass123!",
                "full_name": "Login User"
            }
        )

        # Then login
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "login@example.com",
                "password": "SecurePass123!"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data


@pytest.mark.anyio
async def test_create_monitor():
    """Test creating a monitor"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Register and get token
        reg_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "monitor@example.com",
                "username": "monitoruser",
                "password": "SecurePass123!",
            }
        )

        token = reg_response.json()["access_token"]
        workspace_id = reg_response.json()["user"]["id"]  # TODO: Get actual workspace_id

        # Create monitor
        response = await client.post(
            f"/api/v1/monitors?workspace_id={workspace_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Test Monitor",
                "url": "https://example.com",
                "monitor_type": "https",
                "interval_seconds": 300
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Monitor"
