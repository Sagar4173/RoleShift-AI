"""Organization routes.

Phase 6.3: organizations are tenant-context resources, not an enumeration.
Listing and detail access expose ONLY the authenticated user's own
organization; organization creation via the API is removed (provisioning
belongs to later phases). A foreign or missing organization id is a 404.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_organization
from app.core.exceptions import AppError
from app.models.organization import Organization
from app.schemas.common import ObjectIdStr, Page, PageMeta, pagination_params
from app.schemas.organization import OrganizationRead

router = APIRouter(prefix="/organizations", tags=["organizations"])


def _org_id(organization: Organization) -> ObjectIdStr:
    """Non-None organization id (loaded documents always carry one)."""
    if organization.id is None:
        raise AppError(
            "Failed to resolve organization context",
            code="internal_error",
            status_code=500,
        )
    return organization.id


@router.get("", response_model=Page[OrganizationRead])
async def list_organizations(
    pagination: tuple[int, int] = Depends(pagination_params),
    organization: Organization = Depends(get_current_organization),
) -> Page[OrganizationRead]:
    """Return the authenticated user's organization only.

    Arbitrary organization enumeration is not exposed: another tenant's
    organization never appears in this list.
    """
    skip, limit = pagination
    items = [OrganizationRead.model_validate(organization)]
    total = 1
    return Page[OrganizationRead](
        items=items, meta=PageMeta(skip=skip, limit=limit, total=total)
    )


@router.get("/{organization_id}", response_model=OrganizationRead)
async def get_organization(
    organization_id: ObjectIdStr,
    organization: Organization = Depends(get_current_organization),
) -> OrganizationRead:
    """Return the organization only when it is the caller's own (else 404)."""
    if organization_id != _org_id(organization):
        raise AppError(
            "Organization not found",
            code="organization_not_found",
            status_code=404,
        )
    return OrganizationRead.model_validate(organization)