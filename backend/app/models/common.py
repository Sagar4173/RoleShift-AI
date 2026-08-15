"""Base document with automatic timestamps."""

from __future__ import annotations

from datetime import UTC, datetime

from beanie import Document
from pydantic import Field


class BaseDocument(Document):
    """Base for all RoleShift documents.

    ``updated_at`` is maintained by the repository layer on updates.
    """

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def touch(self) -> None:
        """Refresh the updated_at timestamp before a save."""
        self.updated_at = datetime.now(UTC)