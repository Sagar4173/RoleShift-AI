"""Organization routes.

Phase 6.3: organizations are tenant-context resources, not an enumeration.
Listing and detail access expose ONLY the authenticated user's own
organization; organization creation via the API is removed (provisioning
belongs to later phases). A foreign or missing organization id is a 404.

Phase 6.4: member management (roster, role changes, removal) lives under
/ organizations/members — declared BEFORE the parameterized detail route so
"members" is never parsed as an organization id. Role changes and removals
enforce the owner-safety invariants in MembershipService.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import (
    ensure_roles,
    get_current_membership,
    get_current_organization,
    require_roles,
)
from app.core.exceptions import AppError
from app.models.enums import MemberRole
from app.models.organization import Organization
from app.models.organization_membership import OrganizationMembership
from app.schemas.common import ObjectIdStr, Page, PageMeta, pagination_params
from app.schemas.membership import MemberRead, MemberRoleUpdate
from app.schemas.organization import OrganizationRead
from app.repositories.user import UserRepository
from app.services.membership_service import MembershipService

router = APIRouter(prefix="/organizations", tags=["organizations"])

MEMBER_MANAGER_ROLES = (MemberRole.OWNER, MemberRole.ADMIN)


def _org_id(organization: Organization) -> ObjectIdStr:
    """Non-None organization id (loaded documents always carry one)."""
    if organization.id is None:
        raise AppError(
            "Failed to resolve organization context",
            code="internal_error",
            status_code=500,
        )
    return organization.id


@router.get("/members", response_model=Page[MemberRead])
async def list_members(
    pagination: tuple[int, int] = Depends(pagination_params),
    organization: Organization = Depends(get_current_organization),
    _membership: OrganizationMembership = Depends(require_roles(*MEMBER_MANAGER_ROLES)),
) -> Page[MemberRead]:
    """Return the roster of the caller's own organization (OWNER/ADMIN only).

    The roster is tenant-scoped by construction: memberships are keyed to
    the caller's organization, so no other organization's members appear.
    """
    skip, limit = pagination
    roster = await MembershipService().list_members(_org_id(organization), skip=skip, limit=limit)
    return Page[MemberRead](
        items=[MemberRead(**member) for member in roster["items"]],
        meta=PageMeta(skip=skip, limit=limit, total=roster["total"]),
    )


@router.put("/members/{user_id}", response_model=MemberRead)
async def change_member_role(
    user_id: ObjectIdStr,
    payload: MemberRoleUpdate,
    organization: Organization = Depends(get_current_organization),
    membership: OrganizationMembership = Depends(get_current_membership),
) -> MemberRead:
    """Change a member's role, enforcing escalation and owner invariants.

    OWNER may manage every role; ADMIN may only move ANALYST/VIEWER members
    between ANALYST/VIEWER. A target outside the caller's organization is a
    404 (no existence oracle); an illegal change is a 403; demoting the
    last OWNER is a 409.
    """
    ensure_roles(membership, *MEMBER_MANAGER_ROLES)
    changed = await MembershipService().change_role(
        actor=membership,
        organization_id=_org_id(organization),
        target_user_id=user_id,
        new_role=payload.role,
    )
    return await _member_read(organization, changed)


@router.delete("/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    user_id: ObjectIdStr,
    organization: Organization = Depends(get_current_organization),
    membership: OrganizationMembership = Depends(get_current_membership),
) -> Response:
    """Remove a member from the caller's organization.

    The member's sessions are revoked server-side and their organization
    context is cleared, so a removed member is locked out immediately.
    """
    ensure_roles(membership, *MEMBER_MANAGER_ROLES)
    await MembershipService().remove_member(
        actor=membership,
        organization_id=_org_id(organization),
        target_user_id=user_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def _member_read(
    organization: Organization,
    membership: OrganizationMembership,
) -> MemberRead:
    """Serialise a membership with its user profile (caller's org only).

    Looks the user up directly rather than re-searching a paginated roster,
    so a role change can never report 404 merely because the target sorts
    beyond the current page.
    """
    if membership.organization_id != _org_id(organization):
        raise AppError(
            "Member not found",
            code="member_not_found",
            status_code=404,
        )
    user = await UserRepository().get_by_id(membership.user_id)
    if user is None:
        raise AppError(
            "Member not found",
            code="member_not_found",
            status_code=404,
        )
    return MemberRead(
        user_id=str(membership.user_id),
        email=user.email,
        display_name=user.display_name,
        role=membership.role.value,
        joined_at=membership.created_at.isoformat(),
    )


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