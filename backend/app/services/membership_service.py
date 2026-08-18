"""Organization membership service (Phase 6.4 RBAC).

Owns every authorization decision that involves member roles:

- registration assigns the first user of an organization OWNER and every
  later user VIEWER (idempotent by construction: the decision depends only
  on whether an OWNER membership already exists);
- role changes and removals enforce the owner-safety invariants:
  an organization can never reach zero OWNERs, only OWNERs may create or
  modify OWNER memberships, ADMINs may only manage ANALYST/VIEWER members,
  and every operation is scoped to the actor's organization (a foreign
  member is a 404, never a 403 — no existence oracle).

The repository layer stays data-only; all rules live here.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from weakref import WeakKeyDictionary

from beanie import PydanticObjectId

from app.core.exceptions import AppError, ConflictError
from app.models.enums import MemberRole
from app.models.organization_membership import OrganizationMembership
from app.models.user import User
from app.repositories.membership import MembershipRepository
from app.repositories.user import UserRepository
from app.services.auth.session_service import SessionService

MANAGER_ROLES = (MemberRole.OWNER, MemberRole.ADMIN)

# Serializes owner-mutating operations per (organization, event loop): closes
# the check-then-act window on the last-owner invariant. Keying by loop keeps
# the lock portable across the app loop and per-client test loops (locks are
# loop-bound in asyncio). This guards a single-process deployment (one uvicorn
# worker); multi-worker deployments need a MongoDB transaction or a
# distributed lock instead.
_org_locks: dict[str, WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Lock]] = defaultdict(
    WeakKeyDictionary
)


def _lock_for(organization_id: PydanticObjectId) -> asyncio.Lock:
    loop = asyncio.get_running_loop()
    return _org_locks[str(organization_id)].setdefault(loop, asyncio.Lock())


class MembershipService:
    def __init__(self) -> None:
        self.repository = MembershipRepository()
        self.session_service = SessionService()

    # ------------------------------------------------------------- queries

    async def get_for_user_in_org(
        self,
        user_id: PydanticObjectId | None,
        organization_id: PydanticObjectId | None,
    ) -> OrganizationMembership | None:
        if user_id is None or organization_id is None:
            return None
        return await self.repository.find_for_user_in_org(user_id, organization_id)

    async def role_for_user_in_org(
        self,
        user_id: PydanticObjectId | None,
        organization_id: PydanticObjectId | None,
    ) -> str | None:
        membership = await self.get_for_user_in_org(user_id, organization_id)
        return membership.role.value if membership else None

    async def list_members(
        self,
        organization_id: PydanticObjectId,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> dict:
        """Membership + user profile pairs for the organization's roster."""
        memberships = await self.repository.list_for_org(
            organization_id, skip=skip, limit=limit
        )
        total = await self.repository.count_for_org(organization_id)
        members: list[dict] = []
        for membership in memberships:
            user = await UserRepository().get_by_id(membership.user_id)
            if user is None:
                continue
            members.append(
                {
                    "user_id": str(membership.user_id),
                    "email": user.email,
                    "display_name": user.display_name,
                    "role": membership.role.value,
                    "joined_at": membership.created_at.isoformat(),
                }
            )
        members.sort(key=lambda member: member["email"])
        return {"items": members, "total": total}

    # ----------------------------------------------------------- registration

    async def create_for_registration(
        self,
        *,
        user_id: PydanticObjectId,
        organization_id: PydanticObjectId,
    ) -> OrganizationMembership:
        """Create the membership for a newly registered user.

        The first user of an organization becomes its OWNER (the org anchor);
        every later user starts as VIEWER (the cost-safety floor; promotion
        is an OWNER/ADMIN action). Deterministic and idempotent: the role
        depends only on whether an OWNER already exists.
        """
        role = MemberRole.OWNER if await self.repository.count_owners(organization_id) == 0 else MemberRole.VIEWER
        membership = OrganizationMembership(
            organization_id=organization_id,
            user_id=user_id,
            role=role,
        )
        return await self.repository.create(membership)

    # ----------------------------------------------------------- role changes

    async def change_role(
        self,
        *,
        actor: OrganizationMembership,
        organization_id: PydanticObjectId,
        target_user_id: PydanticObjectId,
        new_role: MemberRole,
    ) -> OrganizationMembership:
        """Change a member's role, enforcing escalation and owner invariants.

        - only OWNERs and ADMINs may change roles;
        - the target must be a member of the actor's organization (404);
        - OWNERs may change any role, including OWNER assignment;
        - ADMINs may only move ANALYST/VIEWER members between ANALYST/VIEWER
          (no OWNER/ADMIN assignment, no touching OWNER or ADMIN members,
          which also blocks any self-elevation);
        - demoting an OWNER is refused (409) when it would leave the
          organization with zero OWNERs (the check and the write are
          serialized per organization to close the race).
        """
        if actor.role not in MANAGER_ROLES:
            raise AppError(
                "Only owners and admins can manage members",
                code="insufficient_permissions",
                status_code=403,
            )

        async with _lock_for(organization_id):
            target = await self.repository.find_for_user_in_org(target_user_id, organization_id)
            if target is None:
                raise AppError(
                    "Member not found",
                    code="member_not_found",
                    status_code=404,
                )

            if actor.role == MemberRole.ADMIN:
                if target.role not in (MemberRole.ANALYST, MemberRole.VIEWER):
                    raise AppError(
                        "Admins can only manage analyst and viewer members",
                        code="insufficient_permissions",
                        status_code=403,
                    )
                if new_role not in (MemberRole.ANALYST, MemberRole.VIEWER):
                    raise AppError(
                        "Admins cannot assign owner or admin roles",
                        code="insufficient_permissions",
                        status_code=403,
                    )

            if (
                target.role == MemberRole.OWNER
                and new_role != MemberRole.OWNER
                and await self.repository.count_owners(organization_id) <= 1
            ):
                raise ConflictError(
                    "An organization must always have at least one owner",
                    code="last_owner",
                )

            target.role = new_role
            return await self.repository.update(target)

    # -------------------------------------------------------------- removal

    async def remove_member(
        self,
        *,
        actor: OrganizationMembership,
        organization_id: PydanticObjectId,
        target_user_id: PydanticObjectId,
    ) -> None:
        """Remove a member from the organization.

        Rules mirror ``change_role`` (only OWNERs/ADMINs may remove; ADMINs
        may only remove ANALYST/VIEWER members; the last OWNER can never be
        removed). On success the user's sessions are revoked first (fail
        closed even if a later step fails), then the membership is deleted
        and the user's session-context pointer is cleared.
        """
        if actor.role not in MANAGER_ROLES:
            raise AppError(
                "Only owners and admins can manage members",
                code="insufficient_permissions",
                status_code=403,
            )

        async with _lock_for(organization_id):
            target = await self.repository.find_for_user_in_org(target_user_id, organization_id)
            if target is None:
                raise AppError(
                    "Member not found",
                    code="member_not_found",
                    status_code=404,
                )

            if actor.role == MemberRole.ADMIN:
                if target.role not in (MemberRole.ANALYST, MemberRole.VIEWER):
                    raise AppError(
                        "Admins can only remove analyst and viewer members",
                        code="insufficient_permissions",
                        status_code=403,
                    )

            if (
                target.role == MemberRole.OWNER
                and await self.repository.count_owners(organization_id) <= 1
            ):
                raise ConflictError(
                    "An organization must always have at least one owner",
                    code="last_owner",
                )

            await SessionService().revoke_all_for_user(target_user_id)
            await self.repository.delete_for_user_in_org(target_user_id, organization_id)

            user = await UserRepository().get_by_id(target_user_id)
            if user is not None and user.organization_id == organization_id:
                user.organization_id = None
                await UserRepository().update(user)