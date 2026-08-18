"""Process routes.

Phase 6.3: processes are organization-scoped. The organization is always
derived from the authenticated user; the client-supplied ``organization_id``
query parameter is no longer part of the contract.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_organization, require_roles
from app.core.exceptions import AppError
from app.models.enums import MemberRole
from app.models.organization import Organization
from app.models.organization_membership import OrganizationMembership
from app.schemas.common import ObjectIdStr, Page, PageMeta, pagination_params
from app.schemas.process import ProcessCreate, ProcessRead
from app.services.process_service import ProcessService

router = APIRouter(prefix="/processes", tags=["processes"])

CONTENT_ROLES = (MemberRole.OWNER, MemberRole.ADMIN, MemberRole.ANALYST)


def _org_id(organization: Organization) -> ObjectIdStr:
    """Non-None organization id (loaded documents always carry one)."""
    if organization.id is None:
        raise AppError(
            "Failed to resolve organization context",
            code="internal_error",
            status_code=500,
        )
    return organization.id


@router.get("", response_model=Page[ProcessRead])
async def list_processes(
    pagination: tuple[int, int] = Depends(pagination_params),
    organization: Organization = Depends(get_current_organization),
    service: ProcessService = Depends(),
) -> Page[ProcessRead]:
    skip, limit = pagination
    items, total = await service.list(
        organization_id=_org_id(organization), skip=skip, limit=limit
    )
    read_items = [ProcessRead.model_validate(item) for item in items]
    return Page[ProcessRead](
        items=read_items, meta=PageMeta(skip=skip, limit=limit, total=total)
    )


@router.get("/{process_id}", response_model=ProcessRead)
async def get_process(
    process_id: ObjectIdStr,
    organization: Organization = Depends(get_current_organization),
    service: ProcessService = Depends(),
) -> ProcessRead:
    """Return a process only when it belongs to the caller's organization."""
    process = await service.get(process_id, _org_id(organization))
    return ProcessRead.model_validate(process)


@router.post("", response_model=ProcessRead, status_code=status.HTTP_201_CREATED)
async def create_process(
    payload: ProcessCreate,
    organization: Organization = Depends(get_current_organization),
    _membership: OrganizationMembership = Depends(require_roles(*CONTENT_ROLES)),
    service: ProcessService = Depends(),
) -> ProcessRead:
    process = await service.create(payload, _org_id(organization))
    return ProcessRead.model_validate(process)