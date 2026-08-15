"""Dashboard / workforce-analytics routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.schemas.dashboard import DashboardSummary, SkillsSummary
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def dashboard_summary(
    service: DashboardService = Depends(),
) -> DashboardSummary:
    """Aggregate workforce-analytics summary from persisted analysis data."""
    return await service.summary()


@router.get("/skills", response_model=SkillsSummary)
async def skills_summary(
    service: DashboardService = Depends(),
) -> SkillsSummary:
    """Future-skill demand aggregated across analyzed roles."""
    return await service.skills_summary()
