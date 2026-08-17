"""Session repository."""

from __future__ import annotations

from datetime import UTC, datetime

from beanie import PydanticObjectId

from app.models.session import Session
from app.repositories.base import BaseRepository


class SessionRepository(BaseRepository[Session]):
    model = Session

    async def find_by_token_hash(self, token_hash: str) -> Session | None:
        return await Session.find_one(Session.token_hash == token_hash)

    async def delete_by_token_hash(self, token_hash: str) -> None:
        await Session.find_one(Session.token_hash == token_hash).delete()

    async def delete_expired(self) -> int:
        """Remove expired sessions, returning the number deleted."""
        # MongoDB stores datetimes as naive UTC; compare with a naive value.
        now = datetime.now(UTC).replace(tzinfo=None)
        expired = await Session.find(Session.expires_at <= now).to_list()
        for session in expired:
            await session.delete()
        return len(expired)

    async def delete_for_user(self, user_id: PydanticObjectId) -> None:
        sessions = await Session.find(Session.user_id == user_id).to_list()
        for session in sessions:
            await session.delete()