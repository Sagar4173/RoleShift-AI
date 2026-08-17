"""Shared FastAPI dependencies."""

from __future__ import annotations

from fastapi import Request

from app.core.config import Settings
from app.core.exceptions import AppError
from app.models.user import User
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