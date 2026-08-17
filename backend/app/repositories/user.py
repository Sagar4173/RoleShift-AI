"""User repository."""

from __future__ import annotations

from typing import Any

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def find_by_email(self, email: str) -> User | None:
        return await User.find_one(User.email == email)

    async def find_by_filter(self, filters: dict[str, Any]) -> User | None:
        return await User.find_one(filters)