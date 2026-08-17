"""Activity document."""

from __future__ import annotations

from beanie import PydanticObjectId
from pydantic import Field

from app.models.common import BaseDocument
from app.models.enums import HumanInvolvement


class Activity(BaseDocument):
    organization_id: PydanticObjectId
    process_id: PydanticObjectId
    role_id: PydanticObjectId
    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    sequence: int = Field(default=0, ge=0, le=10000)
    current_human_involvement: HumanInvolvement = HumanInvolvement.FULL

    class Settings:
        name = "activities"
        indexes = [
            [("process_id", 1), ("role_id", 1)],
            "role_id",
            [("organization_id", 1), ("role_id", 1)],
            [("organization_id", 1), ("process_id", 1)],
        ]