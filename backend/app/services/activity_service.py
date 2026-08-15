"""Activity service."""

from __future__ import annotations

from app.core.exceptions import NotFoundError
from app.models.activity import Activity
from app.repositories.activity import ActivityRepository
from app.schemas.activity import ActivityCreate


class ActivityService:
    def __init__(self) -> None:
        self.repository = ActivityRepository()

    async def create(self, payload: ActivityCreate) -> Activity:
        return await self.repository.create(Activity(**payload.model_dump()))

    async def get(self, activity_id) -> Activity:
        activity = await self.repository.get_by_id(activity_id)
        if activity is None:
            raise NotFoundError("Activity not found", code="activity_not_found")
        return activity

    async def list(
        self,
        *,
        role_id=None,
        process_id=None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Activity], int]:
        filters: dict = {}
        if role_id is not None:
            filters["role_id"] = role_id
        if process_id is not None:
            filters["process_id"] = process_id
        activities = await self.repository.list(
            skip=skip, limit=limit, filters=filters or None, sort=("sequence", 1)
        )
        total = await self.repository.count(filters or None)
        return activities, total