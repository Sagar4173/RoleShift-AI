"""Session lifecycle service: create, validate, and revoke sessions."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from beanie import PydanticObjectId

from app.core.config import Settings
from app.core.exceptions import AppError
from app.models.session import Session
from app.models.user import User
from app.repositories.session import SessionRepository
from app.services.auth.security import hash_token, new_session_token


class SessionService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.repository = SessionRepository()

    def cookie_name(self) -> str:
        return self.settings.auth_cookie_name

    async def create(self, user_id: PydanticObjectId) -> tuple[str, Session]:
        """Create a session, returning (raw_token, session).

        The raw token is returned exactly once (to be placed in the cookie);
        only its hash is stored.
        """
        raw_token = new_session_token()
        session = Session(
            user_id=user_id,
            token_hash=hash_token(raw_token),
            expires_at=datetime.now(UTC) + timedelta(hours=self.settings.auth_session_ttl_hours),
        )
        await self.repository.create(session)
        return raw_token, session

    async def get_user_for_token(self, token: str | None) -> User | None:
        """Resolve a raw cookie token to an active user, or None."""
        if not token:
            return None
        session = await self.repository.find_by_token_hash(hash_token(token))
        if session is None:
            return None
        expires_at = session.expires_at
        if expires_at.tzinfo is None:
            # MongoDB returns datetimes as naive UTC; normalise before comparing.
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at <= datetime.now(UTC):
            return None
        user = await User.get(session.user_id)
        if user is None or not user.is_active:
            return None
        return user

    async def revoke(self, token: str | None) -> None:
        """Revoke a session token (idempotent: missing/expired tokens are fine)."""
        if not token:
            return
        await self.repository.delete_by_token_hash(hash_token(token))

    async def prune_expired(self) -> None:
        """Best-effort cleanup of expired sessions."""
        try:
            await self.repository.delete_expired()
        except Exception:
            pass