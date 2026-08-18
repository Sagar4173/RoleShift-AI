"""Skill routes.

Phase 6.4: the skill catalogue is intentionally GLOBAL (no organization
scoping — Phase 6.3 design). Because a created skill is shared system-wide,
creation is restricted to OWNER/ADMIN on every path: the direct POST /skills
endpoint AND implicit catalogue extension through role content flows
(analyze-new / current-skills). ANALYSTs may only use existing catalogue
skills — a missing name is a 422, never a silent global write. Listing
remains open to all roles.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import rate_limit_by_user, require_roles
from app.models.enums import MemberRole
from app.models.organization_membership import OrganizationMembership
from app.schemas.common import Page, PageMeta, pagination_params
from app.schemas.skill import SkillCreate, SkillRead
from app.services.skill_service import SkillService

router = APIRouter(prefix="/skills", tags=["skills"])

SKILL_WRITE_ROLES = (MemberRole.OWNER, MemberRole.ADMIN)


@router.get("", response_model=Page[SkillRead])
async def list_skills(
    category: str | None = Query(default=None, max_length=100),
    pagination: tuple[int, int] = Depends(pagination_params),
    service: SkillService = Depends(),
) -> Page[SkillRead]:
    skip, limit = pagination
    items, total = await service.list(category=category, skip=skip, limit=limit)
    return Page[SkillRead](items=items, meta=PageMeta(skip=skip, limit=limit, total=total))


@router.post("", response_model=SkillRead, status_code=status.HTTP_201_CREATED)
async def create_skill(
    payload: SkillCreate,
    _membership: OrganizationMembership = Depends(require_roles(*SKILL_WRITE_ROLES)),
    _rate: None = Depends(rate_limit_by_user("skill_create")),
    service: SkillService = Depends(),
) -> SkillRead:
    skill = await service.create(payload)
    return SkillRead.model_validate(skill)