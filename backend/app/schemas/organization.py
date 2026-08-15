"""Organization schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.schemas.common import ObjectIdStr

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class OrganizationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Name
    industry: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=100)] = None
    description: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=2000)] = None


class OrganizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: ObjectIdStr
    name: str
    industry: str | None
    description: str | None
    created_at: datetime
    updated_at: datetime