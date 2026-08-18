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

    async def get_by_normalized_name(self, normalized_name: str) -> Skill | None:
        """Return the catalogue skill whose canonical name matches, if any.

        ``normalized_name`` must already be in canonical form (stripped,
        lower-cased). The unique index on ``normalized_name`` guarantees at
        most one document matches.
        """
        results = await self.list(limit=1, filters={"normalized_name": normalized_name})
        return results[0] if results else None