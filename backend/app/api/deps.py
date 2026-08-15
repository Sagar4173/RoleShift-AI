"""Shared FastAPI dependencies."""

from __future__ import annotations

from fastapi import Request

from app.core.config import Settings


def get_settings_dep(request: Request) -> Settings:
    """FastAPI dependency exposing the active application settings.

    Reads from ``app.state`` (set by the application factory) so tests and
    deployments can inject their own settings without touching globals.
    """
    return request.app.state.settings