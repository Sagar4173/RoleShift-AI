"""Activity routes.

Phase 6.3: activities are organization-scoped. Creation validates that the
referenced process and role belong to the caller's organization; a foreign
reference is a 404 and nothing is created.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_current_organization
from app.core.exceptions import AppError
from app.models.organization import Organization
from app.schemas.activity import ActivityCreate, ActivityRead
from app.schemas.common import ObjectIdStr, Page, PageMeta, pagination_params
from app.services.activity_service import ActivityService

router = APIRouter(prefix="/activities", tags=["activities"])


def _org_id(organization: Organization) -> ObjectIdStr:
    """Non-None organization id (loaded documents always carry one)."""
    if organization.id is None:
        raise AppError(
            "Failed to resolve organization context",
            code="internal_error",
            status_code=500,
        )
    return organization.id


@router.get("", response_model=Page[ActivityRead])
async def list_activities(
    role_id: ObjectIdStr | None = Query(default=None),
    process_id: ObjectIdStr | None = Query(default=None),
    pagination: tuple[int, int] = Depends(pagination_params),
    organization: Organization = Depends(get_current_organization),
    service: ActivityService = Depends(),
) -> Page[ActivityRead]:
    skip, limit = pagination
    items, total = await service.list(
        organization_id=_org_id(organization),
        role_id=role_id,
        process_id=process_id,
        skip=skip,
        limit=limit,
    )
    read_items = [ActivityRead.model_validate(item) for item in items]
    return Page[ActivityRead](
        items=read_items, meta=PageMeta(skip=skip, limit=limit, total=total)
    )


@router.post("", response_model=ActivityRead, status_code=status.HTTP_201_CREATED)
async def create_activity(
    payload: ActivityCreate,
    organization: Organization = Depends(get_current_organization),
    service: ActivityService = Depends(),
) -> ActivityRead:
    activity = await service.create(payload, _org_id(organization))
    return ActivityRead.model_validate(activity)