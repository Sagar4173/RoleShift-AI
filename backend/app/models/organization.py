"""Organization document."""

from __future__ import annotations

from pydantic import Field

from app.models.common import BaseDocument


class Organization(BaseDocument):
    name: str = Field(min_length=1, max_length=120)
    industry: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=2000)

    class Settings:
        name = "organizations"
        indexes = ["industry"]