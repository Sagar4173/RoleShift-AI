"""Dashboard / workforce-analytics routes.

Phase 6.3: every aggregation is scoped to the authenticated user's
organization, so a user never sees another tenant's role counts, role
names, exposure data, or skill demand.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_organization
from app.core.exceptions import AppError
from app.models.organization import Organization
from app.schemas.common import ObjectIdStr
from app.schemas.dashboard import DashboardSummary, SkillsSummary
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _org_id(organization: Organization) -> ObjectIdStr:
    """Non-None organization id (loaded documents always carry one)."""
    if organization.id is None:
        raise AppError(
            "Failed to resolve organization context",
            code="internal_error",
            status_code=500,
        )
    return organization.id


@router.get("/summary", response_model=DashboardSummary)
async def dashboard_summary(
    organization: Organization = Depends(get_current_organization),
    service: DashboardService = Depends(),
) -> DashboardSummary:
    """Aggregate workforce-analytics summary for the caller's organization."""
    return await service.summary(_org_id(organization))


@router.get("/skills", response_model=SkillsSummary)
async def skills_summary(
    organization: Organization = Depends(get_current_organization),
    service: DashboardService = Depends(),
) -> SkillsSummary:
    """Future-skill demand aggregated across the caller's organization's roles."""
    return await service.skills_summary(_org_id(organization))