"""Role CRUD tests (Phase 6.3: organization-scoped)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import create_organization, create_role


def test_create_role(client: TestClient) -> None:
    org = create_organization(client)
    role = create_role(client, org["id"], name="Risk Analyst")
    assert role["name"] == "Risk Analyst"
    assert role["organization_id"] == org["id"]
    assert role["status"] == "active"


def test_get_role(client: TestClient) -> None:
    org = create_organization(client)
    role = create_role(client, org["id"])
    response = client.get(f"/api/v1/roles/{role['id']}")
    assert response.status_code == 200
    assert response.json()["name"] == "Data Analyst"


def test_get_missing_role_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/roles/507f1f77bcf86cd799439011")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "role_not_found"


def test_list_roles_returns_only_current_organization(client: TestClient) -> None:
    """Listing is always scoped to the caller's organization.

    A client-supplied organization_id query parameter is no longer part of
    the contract: it cannot widen the scope to another tenant.
    """
    create_role(client, "ignored", name="Role A")
    create_role(client, "ignored", name="Role B")

    response = client.get("/api/v1/roles")
    body = response.json()
    assert body["meta"]["total"] == 2
    assert {item["name"] for item in body["items"]} == {"Role A", "Role B"}

    # A foreign organization id in the query string must not expose other
    # tenants' roles (the parameter is ignored by the API contract).
    foreign = "507f1f77bcf86cd799439099"
    response = client.get(f"/api/v1/roles?organization_id={foreign}")
    body = response.json()
    assert body["meta"]["total"] == 2


def test_create_role_ignores_client_supplied_organization(client: TestClient) -> None:
    """An organization_id in the create body is rejected (422, extra field)."""
    response = client.post(
        "/api/v1/roles",
        json={"name": "Analyst", "organization_id": "507f1f77bcf86cd799439099"},
    )
    assert response.status_code == 422


def test_delete_role(client: TestClient) -> None:
    org = create_organization(client)
    role = create_role(client, org["id"])

    response = client.delete(f"/api/v1/roles/{role['id']}")
    assert response.status_code == 204

    response = client.get(f"/api/v1/roles/{role['id']}")
    assert response.status_code == 404