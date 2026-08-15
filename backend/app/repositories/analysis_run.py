"""AnalysisRun repository."""

from __future__ import annotations

from beanie import PydanticObjectId
from pymongo import DESCENDING

from app.models.analysis_run import AnalysisRun
from app.models.enums import AnalysisRunStatus
from app.repositories.base import BaseRepository


class AnalysisRunRepository(BaseRepository[AnalysisRun]):
    model = AnalysisRun

    async def find_completed_by_input_hash(
        self, input_hash: str
    ) -> AnalysisRun | None:
        """Return the most recent completed run with this input hash, if any."""
        results = await self.list(
            limit=1,
            filters={"input_hash": input_hash, "status": AnalysisRunStatus.COMPLETED},
            sort=("started_at", -1),
        )
        return results[0] if results else None

    async def latest_for_role(self, role_id: PydanticObjectId) -> AnalysisRun | None:
        """Most recent run (any status) for a role."""
        results = await self.list(
            limit=1,
            filters={"role_id": role_id},
            sort=("started_at", -1),
        )
        return results[0] if results else None
