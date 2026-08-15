"""Activity schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models.enums import HumanInvolvement
from app.schemas.common import ObjectIdStr

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]


class ActivityCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    process_id: ObjectIdStr
    role_id: ObjectIdStr
    name: Name
    description: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=2000)] = None
    sequence: int = Field(default=0, ge=0, le=10000)
    current_human_involvement: HumanInvolvement = HumanInvolvement.FULL


class ActivityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: ObjectIdStr
    process_id: ObjectIdStr
    role_id: ObjectIdStr
    name: str
    description: str | None
    sequence: int
    current_human_involvement: HumanInvolvement
    created_at: datetime
    updated_at: datetime