"""Shared FastAPI dependencies."""

from __future__ import annotations

from fastapi import Depends, Request

from app.core.config import Settings
from app.core.exceptions import AppError
from app.models.organization import Organization
from app.models.user import User
from app.repositories.organization import OrganizationRepository
from app.services.auth.session_service import SessionService


def get_settings_dep(request: Request) -> Settings:
    """FastAPI dependency exposing the active application settings.

    Reads from ``app.state`` (set by the application factory) so tests and
    deployments can inject their own settings without touching globals.
    """
    return request.app.state.settings


async def get_current_user(request: Request) -> User:
    """Authenticate the request via the HttpOnly session cookie.

    Raises 401 (matching the application error contract) when the session
    is missing, unknown, expired, or bound to a disabled user.
    """
    settings = get_settings_dep(request)
    token = request.cookies.get(settings.auth_cookie_name)
    if not token:
        raise AppError("Authentication required", code="unauthorized", status_code=401)
    user = await SessionService(settings).get_user_for_token(token)
    if user is None:
        raise AppError("Session is invalid or has expired", code="unauthorized", status_code=401)
    return user


async def get_current_organization(user: User = Depends(get_current_user)) -> Organization:
    """Resolve the canonical organization context for the authenticated user.

    The organization is always derived from the user's own binding — never
    from client-supplied values. A user without an organization binding, or
    whose organization no longer exists, is refused (403) rather than
    silently granted a tenant context.
    """
    if user.organization_id is None:
        raise AppError(
            "User has no organization context",
            code="organization_required",
            status_code=403,
        )
    organization = await OrganizationRepository().get_by_id(user.organization_id)
    if organization is None:
        raise AppError(
            "Organization not found",
            code="organization_not_found",
            status_code=403,
        )
    return organization