"""Organization membership repository."""

from __future__ import annotations

from beanie import PydanticObjectId

from app.models.organization_membership import OrganizationMembership
from app.repositories.base import BaseRepository


class MembershipRepository(BaseRepository[OrganizationMembership]):
    model = OrganizationMembership

    async def find_for_user_in_org(
        self,
        user_id: PydanticObjectId,
        organization_id: PydanticObjectId,
    ) -> OrganizationMembership | None:
        return await OrganizationMembership.find_one(
            OrganizationMembership.user_id == user_id,
            OrganizationMembership.organization_id == organization_id,
        )

    async def list_for_org(
        self,
        organization_id: PydanticObjectId,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[OrganizationMembership]:
        return await OrganizationMembership.find(
            OrganizationMembership.organization_id == organization_id
        ).skip(skip).limit(limit).to_list()

    async def count_owners(self, organization_id: PydanticObjectId) -> int:
        from app.models.enums import MemberRole

        return await OrganizationMembership.find(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.role == MemberRole.OWNER,
        ).count()

    async def count_for_org(self, organization_id: PydanticObjectId) -> int:
        return await OrganizationMembership.find(
            OrganizationMembership.organization_id == organization_id
        ).count()

    async def delete_for_user_in_org(
        self,
        user_id: PydanticObjectId,
        organization_id: PydanticObjectId,
    ) -> None:
        membership = await self.find_for_user_in_org(user_id, organization_id)
        if membership is not None:
            await membership.delete()