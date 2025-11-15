"""API v1 Router"""
from fastapi import APIRouter
from app.api.v1 import auth, workspaces, monitors

api_router = APIRouter()

# Include sub-routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(workspaces.router, prefix="/workspaces", tags=["Workspaces"])
api_router.include_router(monitors.router, prefix="/monitors", tags=["Monitors"])
