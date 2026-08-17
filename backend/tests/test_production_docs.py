"""Production documentation hardening tests.

In production (APP_ENV=production) the interactive docs AND the raw
OpenAPI schema must all be disabled (404), while health endpoints keep
working. Development/test environments keep /docs, /redoc, and
/openapi.json enabled (covered by test_health.py).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from beanie import init_beanie
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

from app.core import database
from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def production_client(monkeypatch) -> Iterator[TestClient]:
    """HTTP client with a production-configured app backed by an in-memory DB."""
    mock_client = AsyncMongoMockClient()

    async def _init_db(settings: Settings) -> None:
        await init_beanie(
            database=mock_client["roleshift_production_test"],  # type: ignore[arg-type]
            document_models=database.DOCUMENT_MODELS,
        )
        database._client = mock_client

    async def _close_db() -> None:
        pass

    async def _ping_db() -> float:
        return 1.0

    monkeypatch.setattr(database, "init_db", _init_db)
    monkeypatch.setattr(database, "close_db", _close_db)
    monkeypatch.setattr(database, "ping_db", _ping_db)

    app = create_app(
        settings=Settings(
            app_env="production",
            log_level="WARNING",
            ai_provider="none",
        )
    )
    with TestClient(app) as test_client:
        yield test_client


def test_production_docs_disabled(production_client: TestClient) -> None:
    for path in ["/docs", "/redoc", "/openapi.json"]:
        response = production_client.get(path)
        assert response.status_code == 404, f"{path} must be disabled in production"


def test_production_health_still_served(production_client: TestClient) -> None:
    response = production_client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["environment"] == "production"


def test_production_session_cookie_is_secure(production_client: TestClient) -> None:
    response = production_client.post(
        "/api/v1/auth/register",
        json={
            "email": "prod@roleshift.local",
            "display_name": "Prod User",
            "password": "Str0ng!Password",
        },
    )
    assert response.status_code == 201
    set_cookie = response.headers.get("set-cookie", "").lower()
    assert "secure" in set_cookie
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie
