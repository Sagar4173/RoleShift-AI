"""Source repository."""

from __future__ import annotations

from app.models.source import Source
from app.repositories.base import BaseRepository


class SourceRepository(BaseRepository[Source]):
    model = Source