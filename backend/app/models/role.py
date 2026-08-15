"""Role document."""

from __future__ import annotations

from beanie import PydanticObjectId
from pydantic import Field

from app.models.common import BaseDocument
from app.models.enums import RoleStatus


class Role(BaseDocument):
    organization_id: PydanticObjectId
    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    industry: str | None = Field(default=None, max_length=100)
    status: RoleStatus = RoleStatus.ACTIVE
    current_skill_ids: list[PydanticObjectId] = Field(
        default_factory=list,
        description="Current skills held by the role, referenced against the global skill catalogue",
    )

    class Settings:
        name = "roles"
        indexes = ["organization_id", [("organization_id", 1), ("status", 1)]]