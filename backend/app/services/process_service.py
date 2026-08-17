"""Process service."""

from __future__ import annotations

from beanie import PydanticObjectId

from app.core.exceptions import NotFoundError
from app.models.process import Process
from app.repositories.process import ProcessRepository
from app.schemas.process import ProcessCreate


class ProcessService:
    def __init__(self) -> None:
        self.repository = ProcessRepository()

    async def create(
        self, payload: ProcessCreate, organization_id: PydanticObjectId
    ) -> Process:
        return await self.repository.create(
            Process(organization_id=organization_id, **payload.model_dump())
        )

    async def get(
        self, process_id, organization_id: PydanticObjectId
    ) -> Process:
        process = await self.repository.get_by_id(process_id)
        if process is None or process.organization_id != organization_id:
            raise NotFoundError("Process not found", code="process_not_found")
        return process

    async def list(
        self, *, organization_id: PydanticObjectId, skip: int = 0, limit: int = 50
    ) -> tuple[list[Process], int]:
        filters = {"organization_id": organization_id}
        processes = await self.repository.list(skip=skip, limit=limit, filters=filters)
        total = await self.repository.count(filters)
        return processes, total