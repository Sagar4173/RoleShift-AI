"""User service: registration and credential verification."""

from __future__ import annotations

from app.core.config import Settings
from app.core.exceptions import ConflictError
from app.models.user import User
from app.repositories.user import UserRepository
from app.services.auth.security import hash_password, verify_password


class UserService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.repository = UserRepository()

    def normalize_email(self, email: str) -> str:
        return email.strip().lower()

    async def get_by_email(self, email: str) -> User | None:
        return await self.repository.find_by_email(self.normalize_email(email))

    async def register(self, *, email: str, display_name: str, password: str) -> User:
        """Create a new user, rejecting duplicate emails with a 409 conflict."""
        normalized_email = self.normalize_email(email)
        existing = await self.repository.find_by_email(normalized_email)
        if existing is not None:
            raise ConflictError("An account with this email already exists", code="email_exists")
        user = User(
            email=normalized_email,
            display_name=display_name.strip(),
            password_hash=hash_password(password),
            is_active=True,
        )
        return await self.repository.create(user)

    async def authenticate(self, email: str, password: str) -> User | None:
        """Return the user on valid credentials, else None (no side channel)."""
        user = await self.repository.find_by_email(self.normalize_email(email))
        if user is None or not user.is_active:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user