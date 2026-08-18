"""Skill service."""

from __future__ import annotations

from pymongo.errors import DuplicateKeyError

from app.core.exceptions import AppError, DatabaseError, NotFoundError
from app.core.logging import get_logger
from app.models.skill import Skill
from app.repositories.skill import SkillRepository
from app.schemas.skill import SkillCreate

logger = get_logger("services.skill")


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

    async def get_or_create_by_name(
        self,
        name: str,
        *,
        allow_create: bool = True,
        created: list[Skill] | None = None,
    ) -> Skill:
        """Return the catalogue skill with this name, creating it when absent.

        Names resolve canonically: an exact name match wins, then a
        case/whitespace-insensitive match against the catalogue's unique
        canonical names — so "financial analysis" resolves to the existing
        "Financial Analysis" entry instead of creating a duplicate.

        Creation is race-safe: when two requests create the same canonical
        name concurrently, exactly one insert succeeds; the loser catches the
        duplicate-key condition, re-reads the winner's document, and returns
        it — a lost race is never a fatal error. Only the request that
        actually inserted the document records it on ``created``, so
        transactional callers can compensate exactly the skills this request
        introduced and never touch pre-existing catalogue entries.

        When ``allow_create`` is false (ANALYST content flows), a missing
        name raises a deterministic 422 (``skill_not_found_in_catalogue``)
        instead of a silent global write.
        """
        existing = await self.repository.get_by_name(name)
        if existing is None:
            normalized = name.strip().lower()
            existing = await self.repository.get_by_normalized_name(normalized)
        if existing is not None:
            return existing
        if not allow_create:
            raise AppError(
                "Skill not found in the catalogue: " + name,
                code="skill_not_found_in_catalogue",
                status_code=422,
            )
        try:
            skill = await self.create(SkillCreate(name=name))
        except DatabaseError as exc:
            if not isinstance(exc.__cause__, DuplicateKeyError):
                raise
            winner = await self.repository.get_by_normalized_name(name.strip().lower())
            if winner is None:
                raise
            logger.info(
                "Lost concurrent creation race for skill %r; using the winner's catalogue entry",
                name,
            )
            return winner
        if created is not None:
            created.append(skill)
        return skill