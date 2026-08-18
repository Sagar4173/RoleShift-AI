"""User service: registration and credential verification."""

from __future__ import annotations

from pymongo.errors import DuplicateKeyError

from app.core.config import Settings
from app.core.exceptions import AppError, ConflictError, DatabaseError
from app.models.user import User
from app.repositories.organization import OrganizationRepository
from app.repositories.user import UserRepository
from app.services.auth.security import hash_password, verify_password
from app.services.membership_service import MembershipService


class UserService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.repository = UserRepository()

    def normalize_email(self, email: str) -> str:
        return email.strip().lower()

    async def get_by_email(self, email: str) -> User | None:
        return await self.repository.find_by_email(self.normalize_email(email))

    async def register(self, *, email: str, display_name: str, password: str) -> User:
        """Create a new user, rejecting duplicate emails with a 409 conflict.

        Phase 6.3: every new user is bound to the existing organization
        (the oldest one, deterministically). No organization is ever created
        implicitly, and if no organization exists the registration FAILS
        SAFELY (503) instead of provisioning one.

        Phase 6.4: registration also creates the user's organization
        membership — the first user of an organization becomes its OWNER,
        every later user starts as VIEWER (idempotent: the role depends
        only on whether an OWNER already exists).
        """
        normalized_email = self.normalize_email(email)
        existing = await self.repository.find_by_email(normalized_email)
        if existing is not None:
            raise ConflictError("An account with this email already exists", code="email_exists")
        organizations = await OrganizationRepository().list(limit=1, sort=("created_at", 1))
        if not organizations or organizations[0].id is None:
            raise AppError(
                "Registration is unavailable: no organization is provisioned",
                code="organization_unavailable",
                status_code=503,
            )
        user = User(
            email=normalized_email,
            display_name=display_name.strip(),
            password_hash=hash_password(password),
            organization_id=organizations[0].id,
            is_active=True,
        )
        try:
            created = await self.repository.create(user)
        except DatabaseError as exc:
            if isinstance(exc.__cause__, DuplicateKeyError):
                # Lost a concurrent same-email registration race: the unique
                # email index is authoritative, so surface the conflict.
                raise ConflictError(
                    "An account with this email already exists",
                    code="email_exists",
                ) from exc
            raise
        if created.id is None:  # pragma: no cover - inserted documents always have an id
            raise AppError(
                "Failed to persist new user",
                code="internal_error",
                status_code=500,
            )
        try:
            await MembershipService().create_for_registration(
                user_id=created.id,
                organization_id=organizations[0].id,
            )
        except Exception as exc:
            # Compensating delete: a user without a membership is a dead
            # account (fail-closed 403 everywhere) with no self-healing path.
            try:
                await UserRepository().delete(created)
            except Exception:  # pragma: no cover - best effort compensation
                pass
            raise AppError(
                "Failed to finalize registration",
                code="internal_error",
                status_code=500,
            ) from exc
        return created

    async def authenticate(self, email: str, password: str) -> User | None:
        """Return the user on valid credentials, else None (no side channel)."""
        user = await self.repository.find_by_email(self.normalize_email(email))
        if user is None or not user.is_active:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user