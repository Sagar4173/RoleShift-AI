"""Role schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models.enums import ImpactLevel, ReskillingPriority, RoleStatus
from app.schemas.common import ObjectIdStr

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]


class RoleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Name
    description: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=2000)] = None
    industry: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=100)] = None
    status: RoleStatus = RoleStatus.ACTIVE


class RoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: ObjectIdStr
    organization_id: ObjectIdStr
    name: str
    description: str | None
    industry: str | None
    status: RoleStatus
    created_at: datetime
    updated_at: datetime


class RoleListItemRead(RoleRead):
    """Role list entry enriched with latest-analysis status, when available."""

    has_analysis: bool = False
    ai_exposure_score: float | None = None
    ai_exposure_level: ImpactLevel | None = None
    reskilling_priority: ReskillingPriority | None = None


class RoleCurrentSkillsUpdate(BaseModel):
    """Replace a role's current skills (names resolved against the catalogue)."""

    model_config = ConfigDict(extra="forbid")

    skills: list[Name] = Field(default_factory=list, max_length=200)