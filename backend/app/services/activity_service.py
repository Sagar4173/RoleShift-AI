"""Activity service."""

from __future__ import annotations

from beanie import PydanticObjectId

from app.core.exceptions import NotFoundError
from app.models.activity import Activity
from app.models.process import Process
from app.models.role import Role
from app.repositories.activity import ActivityRepository
from app.repositories.process import ProcessRepository
from app.repositories.role import RoleRepository
from app.schemas.activity import ActivityCreate


class ActivityService:
    def __init__(self) -> None:
        self.repository = ActivityRepository()

    async def create(
        self, payload: ActivityCreate, organization_id: PydanticObjectId
    ) -> Activity:
        """Create an activity inside an organization.

        Nested-resource validation (Phase 6.3): the referenced process and
        role must exist AND belong to the same organization as the
        authenticated user. A foreign or missing reference is treated as a
        404 — the activity is never created against another tenant's
        resources.
        """
        process = await ProcessRepository().get_by_id(payload.process_id)
        if process is None or process.organization_id != organization_id:
            raise NotFoundError("Process not found", code="process_not_found")
        role = await RoleRepository().get_by_id(payload.role_id)
        if role is None or role.organization_id != organization_id:
            raise NotFoundError("Role not found", code="role_not_found")
        return await self.repository.create(
            Activity(organization_id=organization_id, **payload.model_dump())
        )

    async def get(
        self, activity_id, organization_id: PydanticObjectId
    ) -> Activity:
        activity = await self.repository.get_by_id(activity_id)
        if activity is None or activity.organization_id != organization_id:
            raise NotFoundError("Activity not found", code="activity_not_found")
        return activity

    async def list(
        self,
        *,
        organization_id: PydanticObjectId,
        role_id=None,
        process_id=None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Activity], int]:
        filters: dict = {"organization_id": organization_id}
        if role_id is not None:
            filters["role_id"] = role_id
        if process_id is not None:
            filters["process_id"] = process_id
        activities = await self.repository.list(
            skip=skip, limit=limit, filters=filters, sort=("sequence", 1)
        )
        total = await self.repository.count(filters)
        return activities, total