"""Activity repository."""

from __future__ import annotations

from app.models.activity import Activity
from app.repositories.base import BaseRepository


class ActivityRepository(BaseRepository[Activity]):
    model = Activity