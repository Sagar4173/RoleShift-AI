"""Role analysis routes.

Phase 2: POST /roles/{role_id}/analyze runs the AI analysis pipeline.
Phase 6.3: all analysis reads/writes are organization-scoped; analyzing a
role outside the caller's organization is a 404 raised BEFORE any AI
provider invocation.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.deps import (
    ensure_roles,
    get_current_organization,
    get_current_membership,
    get_settings_dep,
)
from app.core.config import Settings
from app.core.exceptions import AppError
from app.models.enums import MemberRole
from app.models.organization import Organization
from app.models.organization_membership import OrganizationMembership
from app.schemas.analysis import AnalysisStatusRead, AnalyzeRequest, RoleAnalysisRead
from app.schemas.common import ObjectIdStr
from app.services.analysis_service import AnalysisService
from app.services.ai.base import AIProviderError
from app.services.role_service import RoleService

router = APIRouter(prefix="/roles", tags=["analysis"])

ANALYZE_ROLES = (MemberRole.OWNER, MemberRole.ADMIN, MemberRole.ANALYST)
FORCE_ROLES = (MemberRole.OWNER, MemberRole.ADMIN)


def _org_id(organization: Organization) -> ObjectIdStr:
    """Non-None organization id (loaded documents always carry one)."""
    if organization.id is None:
        raise AppError(
            "Failed to resolve organization context",
            code="internal_error",
            status_code=500,
        )
    return organization.id


@router.get("/{role_id}/analysis", response_model=AnalysisStatusRead)
async def get_role_analysis(
    role_id: ObjectIdStr,
    organization: Organization = Depends(get_current_organization),
    service: AnalysisService = Depends(),
) -> AnalysisStatusRead:
    """Return the latest persisted analysis for a role (if any).

    A role from another organization is indistinguishable from a missing
    one (404): analysis history is tenant-scoped.
    """
    analysis = await service.get_latest_for_role(role_id, _org_id(organization))
    latest = await service.to_read(analysis) if analysis else None
    return AnalysisStatusRead(role_id=role_id, has_analysis=analysis is not None, latest=latest)


@router.post(
    "/{role_id}/analyze",
    response_model=RoleAnalysisRead,
    status_code=status.HTTP_200_OK,
)
async def analyze_role(
    role_id: ObjectIdStr,
    body: AnalyzeRequest | None = None,
    settings: Settings = Depends(get_settings_dep),
    organization: Organization = Depends(get_current_organization),
    membership: OrganizationMembership = Depends(get_current_membership),
    role_service: RoleService = Depends(),
    service: AnalysisService = Depends(),
) -> RoleAnalysisRead:
    """Run the AI analysis pipeline for a role within the caller's organization.

    Returns the persisted RoleAnalysis. Errors from the AI provider are
    mapped to appropriate HTTP status codes by the centralized handler.
    A foreign role is rejected (404) before any provider call.

    Phase 6.4: analysis is ANALYST+; ``force=true`` (which bypasses the
    org-scoped deduplication cache and guarantees provider spend) is
    ADMIN+. Permission checks run after the org-scoped resource resolution
    so a foreign role is always a 404, never a 403.
    """
    await role_service.get(role_id, _org_id(organization))
    ensure_roles(membership, *ANALYZE_ROLES)
    force = body.force if body else False
    if force:
        ensure_roles(membership, *FORCE_ROLES)
    try:
        analysis = await service.analyze_role(
            role_id,
            settings=settings,
            force=force,
            organization_id=_org_id(organization),
        )
    except AIProviderError as exc:
        # Re-raise with provider-specific status code
        raise AppError(
            exc.message,
            code=exc.code,
            status_code=exc.status_code,
        ) from exc
    return await service.to_read(analysis)