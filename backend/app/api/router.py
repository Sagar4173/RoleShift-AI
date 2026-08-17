"""API router aggregation for /api/v1.

Authentication: every router except ``auth`` (and health, mounted separately
in main.py) is protected by the ``get_current_user`` dependency, so every
application endpoint returns 401 for anonymous requests. Enforcement lives
here at the transport layer — the frontend guards are convenience only.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.api.routes import (
    activities,
    analysis,
    auth,
    dashboard,
    organizations,
    processes,
    roles,
    skills,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(
    organizations.router,
    dependencies=[Depends(get_current_user)],
)
api_router.include_router(roles.router, dependencies=[Depends(get_current_user)])
api_router.include_router(processes.router, dependencies=[Depends(get_current_user)])
api_router.include_router(activities.router, dependencies=[Depends(get_current_user)])
api_router.include_router(skills.router, dependencies=[Depends(get_current_user)])
api_router.include_router(analysis.router, dependencies=[Depends(get_current_user)])
api_router.include_router(dashboard.router, dependencies=[Depends(get_current_user)])