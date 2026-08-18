"""Security headers and request-size hardening tests (Phase 6.5.2)."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Literal

import pytest
from beanie import init_beanie
from fastapi import FastAPI
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

from app.core import database
from app.core.config import Settings
from app.main import create_app
from tests.conftest import seed_default_organization

REQUIRED_HEADERS = {
    "x-content-type-options": "nosniff",
    "referrer-policy": "strict-origin-when-cross-origin",
    "x-frame-options": "DENY",
}


def _make_client(monkeypatch, *, app_env: Literal["development", "staging", "production", "test"]) -> FastAPI:
    mock_client = AsyncMongoMockClient()

    async def _init_db(settings: Settings) -> None:
        await init_beanie(
            database=mock_client["roleshift_test"],
            document_models=database.DOCUMENT_MODELS,
        )
        await seed_default_organization(mock_client)
        database._client = mock_client

    async def _close_db() -> None:
        pass

    async def _ping_db() -> float:
        return 1.0

    monkeypatch.setattr(database, "init_db", _init_db)
    monkeypatch.setattr(database, "close_db", _close_db)
    monkeypatch.setattr(database, "ping_db", _ping_db)

    return create_app(
        Settings(
            app_env=app_env,
            log_level="WARNING",
            ai_provider="none",
            ai_model="deepseek-chat",
            ai_api_key="",
            ollama_api_key="",
            ai_api_base_url="https://api.deepseek.com",
            ai_timeout_seconds=60,
            ai_temperature=0.3,
        )
    )


@pytest.fixture
def test_client(monkeypatch) -> Iterator[TestClient]:
    with TestClient(_make_client(monkeypatch, app_env="test")) as client:
        yield client


@pytest.fixture
def prod_client(monkeypatch) -> Iterator[TestClient]:
    with TestClient(_make_client(monkeypatch, app_env="production")) as client:
        yield client


def test_api_response_carries_security_headers(test_client: TestClient) -> None:
    response = test_client.get("/api/v1/roles")  # 401 — protected endpoint
    assert response.status_code == 401
    for name, value in REQUIRED_HEADERS.items():
        assert response.headers[name] == value
    csp = response.headers["content-security-policy"]
    assert "default-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "strict-transport-security" not in response.headers  # non-production


def test_production_response_includes_hsts(prod_client: TestClient) -> None:
    response = prod_client.get("/health")
    assert response.status_code == 200
    assert response.headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"
    for name, value in REQUIRED_HEADERS.items():
        assert response.headers[name] == value


def test_docs_pages_use_navigation_only_csp(test_client: TestClient) -> None:
    """Dev docs load script/style from CDNs: their CSP must not block that."""
    response = test_client.get("/docs")
    assert response.status_code == 200
    csp = response.headers["content-security-policy"]
    assert "frame-ancestors 'none'" in csp
    assert "default-src" not in csp


def test_oversized_request_body_rejected_with_413(test_client: TestClient) -> None:
    response = test_client.post(
        "/api/v1/auth/register",
        json={
            "email": "x@roleshift.local",
            "display_name": "X",
            "password": "p" * 1_200_000,
        },
    )
    assert response.status_code == 413
    assert response.json() == {
        "detail": {
            "code": "payload_too_large",
            "message": "Request body exceeds the maximum allowed size",
        }
    }
    # The 413 response still carries the security headers.
    assert response.headers["x-content-type-options"] == "nosniff"


def test_normal_request_unaffected_by_hardening(test_client: TestClient) -> None:
    response = test_client.post(
        "/api/v1/auth/register",
        json={
            "email": "user@roleshift.local",
            "display_name": "User",
            "password": "Str0ng!Password",
        },
    )
    assert response.status_code == 201, response.text


def test_vercel_spa_headers_cannot_break_application() -> None:
    """The SPA's headers (served by Vercel) harden framing/navigation without
    restricting scripts or styles, so the built app cannot be broken by them."""
    config_path = Path(__file__).resolve().parents[2] / "frontend" / "vercel.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    spa_headers = {
        header["key"].lower(): header["value"]
        for rule in config["headers"]
        if rule["source"] == "/(.*)"
        for header in rule["headers"]
    }
    assert spa_headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"
    assert spa_headers["x-content-type-options"] == "nosniff"
    assert spa_headers["x-frame-options"] == "DENY"
    csp = spa_headers["content-security-policy"]
    assert "frame-ancestors 'none'" in csp
    assert "script-src" not in csp
    assert "default-src" not in csp