"""API router aggregation for /api/v1."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import (
    activities,
    analysis,
    dashboard,
    organizations,
    processes,
    roles,
    skills,
)

api_router = APIRouter()
api_router.include_router(organizations.router)
api_router.include_router(roles.router)
api_router.include_router(processes.router)
api_router.include_router(activities.router)
api_router.include_router(skills.router)
api_router.include_router(analysis.router)
api_router.include_router(dashboard.router)