"""Process repository."""

from __future__ import annotations

from app.models.process import Process
from app.repositories.base import BaseRepository


class ProcessRepository(BaseRepository[Process]):
    model = Process