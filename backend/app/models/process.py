"""Process document."""

from __future__ import annotations

from beanie import PydanticObjectId
from pydantic import Field

from app.models.common import BaseDocument


class Process(BaseDocument):
    organization_id: PydanticObjectId
    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    industry: str | None = Field(default=None, max_length=100)

    class Settings:
        name = "processes"
        indexes = ["organization_id"]