"""Organization CRUD tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import create_organization


def test_create_organization(client: TestClient) -> None:
    body = create_organization(client, name="Initech")
    assert body["name"] == "Initech"
    assert body["industry"] == "Technology"
    assert body["id"]
    assert body["created_at"]
    assert body["updated_at"]


def test_get_organization(client: TestClient) -> None:
    created = create_organization(client)
    response = client.get(f"/api/v1/organizations/{created['id']}")
    assert response.status_code == 200
    assert response.json()["name"] == "Acme Corp"


def test_get_missing_organization_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/organizations/507f1f77bcf86cd799439011")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "organization_not_found"


def test_list_organizations(client: TestClient) -> None:
    create_organization(client, name="Org A")
    create_organization(client, name="Org B")
    response = client.get("/api/v1/organizations")
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 2
    assert body["meta"] == {"skip": 0, "limit": 50, "total": 2}


def test_list_organizations_paginated(client: TestClient) -> None:
    for index in range(3):
        create_organization(client, name=f"Org {index}")
    response = client.get("/api/v1/organizations?skip=1&limit=1")
    body = response.json()
    assert len(body["items"]) == 1
    assert body["meta"] == {"skip": 1, "limit": 1, "total": 3}