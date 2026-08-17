"""Source document: an external reference used during analysis."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from beanie import PydanticObjectId
from pydantic import Field, StringConstraints

from app.models.common import BaseDocument
from app.models.enums import SourceType

HttpUrlStr = Annotated[str, StringConstraints(max_length=1000)]


class Source(BaseDocument):
    organization_id: PydanticObjectId
    role_id: PydanticObjectId | None = Field(default=None)
    title: str = Field(min_length=1, max_length=300)
    url: HttpUrlStr
    source_type: SourceType = SourceType.OTHER
    publisher: str | None = Field(default=None, max_length=200)
    published_at: datetime | None = None
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    content_hash: str = Field(min_length=64, max_length=64)
    relevance: float = Field(default=0.0, ge=0.0, le=1.0)

    class Settings:
        name = "sources"
        indexes = [
            "content_hash",
            [("role_id", 1), ("relevance", -1)],
            [("organization_id", 1), ("role_id", 1), ("relevance", -1)],
        ]