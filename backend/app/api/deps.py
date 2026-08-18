"""Shared FastAPI dependencies."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeVar

from fastapi import Depends, Request

from app.core.config import Settings
from app.core.exceptions import AppError
from app.models.enums import MemberRole
from app.models.organization import Organization
from app.models.organization_membership import OrganizationMembership
from app.models.user import User
from app.repositories.organization import OrganizationRepository
from app.services.auth.session_service import SessionService
from app.services.membership_service import MembershipService


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


async def get_current_membership(
    user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
) -> OrganizationMembership:
    """Resolve the caller's authorization record for their organization.

    The membership is keyed by (user, organization) — never by any
    client-supplied value. A user without a membership in the resolved
    organization (removed member or inconsistent state) is refused with 403:
    authorization fails closed.
    """
    if user.id is None or organization.id is None:  # pragma: no cover - loaded docs always carry ids
        raise AppError(
            "Failed to resolve membership context",
            code="internal_error",
            status_code=500,
        )
    membership = await MembershipService().get_for_user_in_org(user.id, organization.id)
    if membership is None:
        raise AppError(
            "No membership for this organization",
            code="membership_not_found",
            status_code=403,
        )
    return membership


def require_roles(*roles: MemberRole) -> Callable[..., Awaitable[OrganizationMembership]]:
    """Build a route dependency that requires any of the given roles.

    Use only on routes without an organization-scoped resource parameter:
    for resource routes the 404-before-403 ordering is enforced in the
    handler (resolve the resource first, then check permissions).
    """

    async def _require(
        membership: OrganizationMembership = Depends(get_current_membership),
    ) -> OrganizationMembership:
        ensure_roles(membership, *roles)
        return membership

    return _require


def ensure_roles(membership: OrganizationMembership, *roles: MemberRole) -> None:
    """Raise 403 when the membership's role is not in the allow-list.

    Shared by route dependencies and handler-level checks so the permission
    semantics (and the error contract) stay identical everywhere.
    """
    if membership.role not in roles:
        raise AppError(
            "You don't have permission to perform this action",
            code="insufficient_permissions",
            status_code=403,
        )