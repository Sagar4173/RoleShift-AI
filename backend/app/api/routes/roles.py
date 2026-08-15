"""Role routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.deps import get_settings_dep
from app.core.config import Settings
from app.core.exceptions import AppError
from app.models.role import Role
from app.models.role_analysis import RoleAnalysis
from app.schemas.analysis import (
    AnalyzeNewRequest,
    AnalyzeNewResponse,
    RoleCompareItem,
    RoleCompareResponse,
)
from app.schemas.common import ObjectIdStr, Page, PageMeta, pagination_params
from app.schemas.organization import OrganizationCreate
from app.schemas.role import (
    RoleCreate,
    RoleCurrentSkillsUpdate,
    RoleListItemRead,
    RoleRead,
)
from app.services.analysis_service import AnalysisService
from app.services.ai.base import AIProviderError
from app.services.organization_service import OrganizationService
from app.services.role_service import RoleService

router = APIRouter(prefix="/roles", tags=["roles"])


def _to_list_item(role: Role, analysis: RoleAnalysis | None) -> RoleListItemRead:
    base = RoleRead.model_validate(role).model_dump()
    base["has_analysis"] = analysis is not None
    if analysis is not None:
        base["ai_exposure_score"] = analysis.ai_exposure.score
        base["ai_exposure_level"] = analysis.ai_exposure.level
        base["reskilling_priority"] = analysis.reskilling_priority
    return RoleListItemRead(**base)


async def _default_organization(
    service: OrganizationService,
):
    organizations, _ = await service.list(limit=1)
    if organizations:
        return organizations[0]
    return await service.create(OrganizationCreate(name="Default Organization"))


@router.get("", response_model=Page[RoleListItemRead])
async def list_roles(
    organization_id: ObjectIdStr | None = Query(default=None),
    industry: str | None = Query(default=None),
    search: str | None = Query(default=None),
    pagination: tuple[int, int] = Depends(pagination_params),
    service: RoleService = Depends(),
) -> Page[RoleListItemRead]:
    skip, limit = pagination
    pairs, total = await service.list_with_analysis(
        organization_id=organization_id,
        industry=industry,
        search=search,
        skip=skip,
        limit=limit,
    )
    items = [_to_list_item(role, analysis) for role, analysis in pairs]
    return Page[RoleListItemRead](items=items, meta=PageMeta(skip=skip, limit=limit, total=total))


@router.post("", response_model=RoleRead, status_code=status.HTTP_201_CREATED)
async def create_role(
    payload: RoleCreate,
    service: RoleService = Depends(),
) -> RoleRead:
    role = await service.create(payload)
    return RoleRead.model_validate(role)


@router.post("/analyze-new", response_model=AnalyzeNewResponse, status_code=status.HTTP_201_CREATED)
async def analyze_new_role(
    payload: AnalyzeNewRequest,
    settings: Settings = Depends(get_settings_dep),
    role_service: RoleService = Depends(),
    analysis_service: AnalysisService = Depends(),
    organization_service: OrganizationService = Depends(),
) -> AnalyzeNewResponse:
    """Create a role (with processes, activities, and skills) and run its first analysis.

    The role, its processes/activities/skills, the analysis, and the
    AnalysisRun records are all persisted. Returns both so the UI can
    navigate straight to the role's intelligence view.
    """
    organization = await _default_organization(organization_service)
    if organization.id is None:
        raise AppError(
            "Failed to resolve organization for new role",
            code="internal_error",
            status_code=500,
        )
    role = await role_service.create_with_context(
        organization_id=organization.id,
        name=payload.name,
        description=payload.description,
        industry=payload.industry,
        processes=payload.processes,
        current_skills=payload.current_skills,
    )
    if role.id is None:
        raise AppError(
            "Failed to persist new role",
            code="internal_error",
            status_code=500,
        )
    try:
        analysis = await analysis_service.analyze_role(
            role.id, settings=settings, force=False
        )
    except AIProviderError as exc:
        raise AppError(
            exc.message,
            code=exc.code,
            status_code=exc.status_code,
        ) from exc
    return AnalyzeNewResponse(
        role=RoleRead.model_validate(role),
        analysis=await analysis_service.to_read(analysis),
    )


@router.get("/compare", response_model=RoleCompareResponse)
async def compare_roles(
    role_ids: list[ObjectIdStr] = Query(default=[]),
    role_service: RoleService = Depends(),
    analysis_service: AnalysisService = Depends(),
) -> RoleCompareResponse:
    """Return role + latest-analysis pairs for side-by-side comparison."""
    items: list[RoleCompareItem] = []
    for role_id in role_ids:
        role = await role_service.get(role_id)
        analysis = await analysis_service.get_latest_for_role(role_id)
        items.append(
            RoleCompareItem(
                role=RoleRead.model_validate(role),
                has_analysis=analysis is not None,
                analysis=(
                    await analysis_service.to_read(analysis) if analysis else None
                ),
            )
        )
    return RoleCompareResponse(roles=items)


@router.put("/{role_id}/current-skills", response_model=RoleRead)
async def update_role_current_skills(
    role_id: ObjectIdStr,
    payload: RoleCurrentSkillsUpdate,
    role_service: RoleService = Depends(),
) -> RoleRead:
    """Replace the role's current skills (resolved against the catalogue)."""
    role = await role_service.set_current_skills(role_id, payload.skills)
    return RoleRead.model_validate(role)


@router.get("/{role_id}", response_model=RoleRead)
async def get_role(
    role_id: ObjectIdStr,
    service: RoleService = Depends(),
) -> RoleRead:
    role = await service.get(role_id)
    return RoleRead.model_validate(role)


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: ObjectIdStr,
    service: RoleService = Depends(),
) -> Response:
    await service.delete(role_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
