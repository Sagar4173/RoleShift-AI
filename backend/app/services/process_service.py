"""Process service."""

from __future__ import annotations

from app.core.exceptions import NotFoundError
from app.models.process import Process
from app.repositories.process import ProcessRepository
from app.schemas.process import ProcessCreate


class ProcessService:
    def __init__(self) -> None:
        self.repository = ProcessRepository()

    async def create(self, payload: ProcessCreate) -> Process:
        return await self.repository.create(Process(**payload.model_dump()))

    async def get(self, process_id) -> Process:
        process = await self.repository.get_by_id(process_id)
        if process is None:
            raise NotFoundError("Process not found", code="process_not_found")
        return process

    async def list(
        self, *, organization_id=None, skip: int = 0, limit: int = 50
    ) -> tuple[list[Process], int]:
        filters = {"organization_id": organization_id} if organization_id else None
        processes = await self.repository.list(skip=skip, limit=limit, filters=filters)
        total = await self.repository.count(filters)
        return processes, total