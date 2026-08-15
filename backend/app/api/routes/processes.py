"""Process routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.schemas.common import ObjectIdStr, Page, PageMeta, pagination_params
from app.schemas.process import ProcessCreate, ProcessRead
from app.services.process_service import ProcessService

router = APIRouter(prefix="/processes", tags=["processes"])


@router.get("", response_model=Page[ProcessRead])
async def list_processes(
    organization_id: ObjectIdStr | None = Query(default=None),
    pagination: tuple[int, int] = Depends(pagination_params),
    service: ProcessService = Depends(),
) -> Page[ProcessRead]:
    skip, limit = pagination
    items, total = await service.list(organization_id=organization_id, skip=skip, limit=limit)
    return Page[ProcessRead](items=items, meta=PageMeta(skip=skip, limit=limit, total=total))


@router.post("", response_model=ProcessRead, status_code=status.HTTP_201_CREATED)
async def create_process(
    payload: ProcessCreate,
    service: ProcessService = Depends(),
) -> ProcessRead:
    process = await service.create(payload)
    return ProcessRead.model_validate(process)