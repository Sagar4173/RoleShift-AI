"""Skill service."""

from __future__ import annotations

from app.core.exceptions import NotFoundError
from app.models.skill import Skill
from app.repositories.skill import SkillRepository
from app.schemas.skill import SkillCreate


class SkillService:
    def __init__(self) -> None:
        self.repository = SkillRepository()

    async def create(self, payload: SkillCreate) -> Skill:
        return await self.repository.create(Skill(**payload.model_dump()))

    async def get(self, skill_id) -> Skill:
        skill = await self.repository.get_by_id(skill_id)
        if skill is None:
            raise NotFoundError("Skill not found", code="skill_not_found")
        return skill

    async def list(self, *, category=None, skip: int = 0, limit: int = 50) -> tuple[list[Skill], int]:
        filters = {"category": category} if category else None
        skills = await self.repository.list(skip=skip, limit=limit, filters=filters)
        total = await self.repository.count(filters)
        return skills, total

    async def get_or_create_by_name(self, name: str) -> Skill:
        """Return the catalogue skill with this name, creating it if absent."""
        existing = await self.repository.get_by_name(name)
        if existing is not None:
            return existing
        return await self.create(SkillCreate(name=name))