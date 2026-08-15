"""Organization service."""

from __future__ import annotations

from app.core.exceptions import NotFoundError
from app.models.organization import Organization
from app.repositories.organization import OrganizationRepository
from app.schemas.organization import OrganizationCreate


class OrganizationService:
    def __init__(self) -> None:
        self.repository = OrganizationRepository()

    async def create(self, payload: OrganizationCreate) -> Organization:
        return await self.repository.create(Organization(**payload.model_dump()))

    async def get(self, organization_id) -> Organization:
        organization = await self.repository.get_by_id(organization_id)
        if organization is None:
            raise NotFoundError("Organization not found", code="organization_not_found")
        return organization

    async def list(self, *, skip: int = 0, limit: int = 50) -> tuple[list[Organization], int]:
        organizations = await self.repository.list(skip=skip, limit=limit)
        total = await self.repository.count()
        return organizations, total