"""Health endpoint tests."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "RoleShift AI"
    assert body["version"]
    assert body["environment"] == "test"


def test_health_does_not_expose_secrets(client: TestClient) -> None:
    response = client.get("/health")
    body = response.json()
    text = response.text.lower()
    assert "mongodb" not in text
    assert "password" not in text
    assert "secret" not in text
    assert set(body) == {"status", "service", "version", "environment", "time"}


def test_health_db(client: TestClient) -> None:
    response = client.get("/health/db")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database"] == "connected"


def test_api_docs_load(client: TestClient) -> None:
    response = client.get("/docs")
    assert response.status_code == 200
    assert "swagger" in response.text.lower()


def test_openapi_describes_expected_endpoints(client: TestClient) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    for path in [
        "/health",
        "/api/v1/organizations",
        "/api/v1/roles",
        "/api/v1/roles/{role_id}",
        "/api/v1/processes",
        "/api/v1/activities",
        "/api/v1/skills",
        "/api/v1/roles/{role_id}/analysis",
    ]:
        assert path in paths, f"missing path {path}"