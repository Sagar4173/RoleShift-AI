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
        self, input_hash: str, organization_id: PydanticObjectId
    ) -> AnalysisRun | None:
        """Most recent completed run with this input hash in this organization, if any.

        Scoped by organization so one tenant can never receive another
        tenant's cached analysis.
        """
        results = await self.list(
            limit=1,
            filters={
                "input_hash": input_hash,
                "status": AnalysisRunStatus.COMPLETED,
                "organization_id": organization_id,
            },
            sort=("started_at", -1),
        )
        return results[0] if results else None

    async def latest_for_role(
        self, role_id: PydanticObjectId, organization_id: PydanticObjectId
    ) -> AnalysisRun | None:
        """Most recent run (any status) for a role within an organization."""
        results = await self.list(
            limit=1,
            filters={
                "role_id": role_id,
                "organization_id": organization_id,
            },
            sort=("started_at", -1),
        )
        return results[0] if results else None
