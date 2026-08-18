"""Skill document."""

from __future__ import annotations

from pydantic import Field, model_validator
from pymongo import IndexModel

from app.models.common import BaseDocument


class Skill(BaseDocument):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    category: str | None = Field(default=None, max_length=100)
    normalized_name: str = Field(
        default="",
        max_length=150,
        description=(
            "Canonical form of the name (stripped, lower-cased) used for "
            "unique catalogue identity, so case/whitespace variants resolve "
            "to the same skill"
        ),
    )

    @model_validator(mode="after")
    def _derive_normalized_name(self) -> "Skill":
        self.normalized_name = (self.name or "").strip().lower()
        return self

    class Settings:
        name = "skills"
        indexes = [
            "category",
            IndexModel(
                [("normalized_name", 1)],
                unique=True,
                partialFilterExpression={"normalized_name": {"$exists": True}},
            ),
        ]