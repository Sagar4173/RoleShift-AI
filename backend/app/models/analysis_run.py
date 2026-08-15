"""AnalysisRun document: tracks an analysis execution for auditability."""

from __future__ import annotations

from datetime import UTC, datetime

from beanie import PydanticObjectId
from pydantic import Field

from app.models.common import BaseDocument
from app.models.enums import AnalysisRunStatus


class AnalysisRun(BaseDocument):
    role_id: PydanticObjectId
    provider: str = Field(default="", max_length=100)
    model: str = Field(min_length=1, max_length=200)
    model_version: str | None = Field(default=None, max_length=100)
    prompt_version: str | None = Field(default=None, max_length=100)
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    status: AnalysisRunStatus = AnalysisRunStatus.PENDING
    input_hash: str | None = Field(default=None, max_length=64)
    role_analysis_id: PydanticObjectId | None = None
    error: str | None = Field(default=None, max_length=4000)

    class Settings:
        name = "analysis_runs"
        indexes = [
            [("role_id", 1), ("status", 1)],
            [("role_id", 1), ("started_at", -1)],
            [("input_hash", 1), ("status", 1)],
        ]