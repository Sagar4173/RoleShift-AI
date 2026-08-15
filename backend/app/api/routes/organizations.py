"""Organization routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status

from app.schemas.common import ObjectIdStr, Page, PageMeta, pagination_params
from app.schemas.organization import OrganizationCreate, OrganizationRead
from app.services.organization_service import OrganizationService

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("", response_model=Page[OrganizationRead])
async def list_organizations(
    pagination: tuple[int, int] = Depends(pagination_params),
    service: OrganizationService = Depends(),
) -> Page[OrganizationRead]:
    skip, limit = pagination
    items, total = await service.list(skip=skip, limit=limit)
    return Page[OrganizationRead](items=items, meta=PageMeta(skip=skip, limit=limit, total=total))


@router.post("", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
async def create_organization(
    payload: OrganizationCreate,
    service: OrganizationService = Depends(),
) -> OrganizationRead:
    organization = await service.create(payload)
    return OrganizationRead.model_validate(organization)


@router.get("/{organization_id}", response_model=OrganizationRead)
async def get_organization(
    organization_id: ObjectIdStr,
    service: OrganizationService = Depends(),
) -> OrganizationRead:
    organization = await service.get(organization_id)
    return OrganizationRead.model_validate(organization)