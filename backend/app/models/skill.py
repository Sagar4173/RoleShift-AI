"""Skill document."""

from __future__ import annotations

from pydantic import Field

from app.models.common import BaseDocument


class Skill(BaseDocument):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    category: str | None = Field(default=None, max_length=100)

    class Settings:
        name = "skills"
        indexes = ["category"]