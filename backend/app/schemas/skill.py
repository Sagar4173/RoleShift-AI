"""Skill schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.schemas.common import ObjectIdStr

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]


class SkillCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Name
    description: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=2000)] = None
    category: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=100)] = None


class SkillRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: ObjectIdStr
    name: str
    description: str | None
    category: str | None
    created_at: datetime
    updated_at: datetime