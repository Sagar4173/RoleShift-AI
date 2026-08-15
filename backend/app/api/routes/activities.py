"""Activity routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.schemas.activity import ActivityCreate, ActivityRead
from app.schemas.common import ObjectIdStr, Page, PageMeta, pagination_params
from app.services.activity_service import ActivityService

router = APIRouter(prefix="/activities", tags=["activities"])


@router.get("", response_model=Page[ActivityRead])
async def list_activities(
    role_id: ObjectIdStr | None = Query(default=None),
    process_id: ObjectIdStr | None = Query(default=None),
    pagination: tuple[int, int] = Depends(pagination_params),
    service: ActivityService = Depends(),
) -> Page[ActivityRead]:
    skip, limit = pagination
    items, total = await service.list(
        role_id=role_id, process_id=process_id, skip=skip, limit=limit
    )
    return Page[ActivityRead](items=items, meta=PageMeta(skip=skip, limit=limit, total=total))


@router.post("", response_model=ActivityRead, status_code=status.HTTP_201_CREATED)
async def create_activity(
    payload: ActivityCreate,
    service: ActivityService = Depends(),
) -> ActivityRead:
    activity = await service.create(payload)
    return ActivityRead.model_validate(activity)