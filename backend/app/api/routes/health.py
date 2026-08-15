"""Health check routes."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from app.core.config import Settings
from app.core.exceptions import DatabaseError
from app.core.logging import get_logger
from app.core import database
from app.api.deps import get_settings_dep

router = APIRouter(tags=["health"])

logger = get_logger("api.routes.health")


@router.get("/health")
async def health(settings: Settings = Depends(get_settings_dep)) -> dict:
    """Liveness probe. Never exposes secrets or connection internals."""
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "time": datetime.now(UTC).isoformat(),
    }


@router.get("/health/db")
async def health_db(settings: Settings = Depends(get_settings_dep)) -> dict:
    """Database readiness probe: pings MongoDB and reports latency."""
    try:
        await database.ping_db()
    except DatabaseError as exc:
        logger.error("Database health check failed: %s", exc.message)
        raise
    return {
        "status": "ok",
        "database": "connected",
        "time": datetime.now(UTC).isoformat(),
    }