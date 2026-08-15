"""Process schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.schemas.common import ObjectIdStr

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]


class ProcessCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: ObjectIdStr
    name: Name
    description: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=2000)] = None
    industry: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=100)] = None


class ProcessRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: ObjectIdStr
    organization_id: ObjectIdStr
    name: str
    description: str | None
    industry: str | None
    created_at: datetime
    updated_at: datetime