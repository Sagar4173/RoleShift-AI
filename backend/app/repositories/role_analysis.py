"""RoleAnalysis repository."""

from __future__ import annotations

from beanie import PydanticObjectId

from app.models.role_analysis import RoleAnalysis
from app.repositories.base import BaseRepository


class RoleAnalysisRepository(BaseRepository[RoleAnalysis]):
    model = RoleAnalysis

    async def latest_for_role(self, role_id: PydanticObjectId) -> RoleAnalysis | None:
        """Most recent analysis for a role (by creation time, newest first)."""
        results = await self.list(
            limit=1,
            filters={"role_id": role_id},
            sort=("created_at", -1),
        )
        return results[0] if results else None

    async def latest_for_roles(
        self, role_ids: list[PydanticObjectId]
    ) -> dict[PydanticObjectId, RoleAnalysis]:
        """Map role_id -> its most recent analysis for a set of roles."""
        if not role_ids:
            return {}
        results = await self.list(
            limit=5000,
            filters={"role_id": {"$in": role_ids}},
        )
        latest: dict[PydanticObjectId, RoleAnalysis] = {}
        for analysis in results:
            if analysis.role_id is None:
                continue
            existing = latest.get(analysis.role_id)
            if existing is None or analysis.created_at > existing.created_at:
                latest[analysis.role_id] = analysis
        return latest

    async def all_grouped_latest(
        self, limit: int = 5000
    ) -> dict[PydanticObjectId, RoleAnalysis]:
        """All analyses grouped by role, keeping the most recent per role."""
        results = await self.list(limit=limit)
        latest: dict[PydanticObjectId, RoleAnalysis] = {}
        for analysis in results:
            if analysis.role_id is None:
                continue
            existing = latest.get(analysis.role_id)
            if existing is None or analysis.created_at > existing.created_at:
                latest[analysis.role_id] = analysis
        return latest

    async def list_recent(self, limit: int = 20) -> list[RoleAnalysis]:
        """Most recent analyses overall (any role), newest first."""
        return await self.list(limit=limit, sort=("created_at", -1))
