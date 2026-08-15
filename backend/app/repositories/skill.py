"""Skill repository."""

from __future__ import annotations

from app.models.skill import Skill
from app.repositories.base import BaseRepository


class SkillRepository(BaseRepository[Skill]):
    model = Skill

    async def get_by_name(self, name: str) -> Skill | None:
        """Return a catalogue skill with the exact name, if any."""
        results = await self.list(limit=1, filters={"name": name})
        return results[0] if results else None