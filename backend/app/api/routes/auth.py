"""Authentication routes: register, login, logout, and current user.

Sessions are server-side: an opaque token is delivered in an HttpOnly,
SameSite=Lax cookie (Secure in non-development environments) and stored
hashed in MongoDB. Logout revokes the session server-side, so the token
is dead even if the cookie survives.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status

from app.api.deps import get_current_user, get_settings_dep
from app.core.config import Settings
from app.core.exceptions import AppError
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, UserRead
from app.services.auth.session_service import SessionService
from app.services.auth.user_service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])


def _session_cookie(
    settings: Settings,
    raw_token: str,
    max_age_seconds: int,
) -> dict:
    return {
        "key": settings.auth_cookie_name,
        "value": raw_token,
        "httponly": True,
        "samesite": "lax",
        "secure": settings.auth_cookie_secure,
        "max_age": max_age_seconds,
        "path": "/",
    }


def _attach_session(response: Response, settings: Settings, raw_token: str, ttl_hours: int) -> None:
    response.set_cookie(**_session_cookie(settings, raw_token, ttl_hours * 3600))


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
) -> UserRead:
    settings = get_settings_dep(request)
    user = await UserService(settings).register(
        email=payload.email,
        display_name=payload.display_name,
        password=payload.password,
    )
    if user.id is None:  # pragma: no cover - inserted documents always have an id
        raise RuntimeError("User created without an id")
    raw_token, _ = await SessionService(settings).create(user.id)
    _attach_session(response, settings, raw_token, settings.auth_session_ttl_hours)
    return UserRead.from_user(user)


@router.post("/login", response_model=UserRead)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
) -> UserRead:
    settings = get_settings_dep(request)
    user = await UserService(settings).authenticate(payload.email, payload.password)
    if user is None:
        raise AppError(
            "Invalid email or password",
            code="invalid_credentials",
            status_code=401,
        )
    await SessionService(settings).prune_expired()
    if user.id is None:  # pragma: no cover - fetched documents always have an id
        raise RuntimeError("User loaded without an id")
    raw_token, _ = await SessionService(settings).create(user.id)
    _attach_session(response, settings, raw_token, settings.auth_session_ttl_hours)
    return UserRead.from_user(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
) -> None:
    settings = get_settings_dep(request)
    raw_token = request.cookies.get(settings.auth_cookie_name)
    await SessionService(settings).revoke(raw_token)
    response.delete_cookie(
        settings.auth_cookie_name,
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.auth_cookie_secure,
    )


@router.get("/me", response_model=UserRead)
async def me(user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.from_user(user)