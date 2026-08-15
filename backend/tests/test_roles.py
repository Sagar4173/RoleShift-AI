"""Role CRUD tests."""

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


def test_list_roles_filtered_by_organization(client: TestClient) -> None:
    org_a = create_organization(client, name="Org A")
    org_b = create_organization(client, name="Org B")
    create_role(client, org_a["id"], name="Role A1")
    create_role(client, org_a["id"], name="Role A2")
    create_role(client, org_b["id"], name="Role B1")

    response = client.get(f"/api/v1/roles?organization_id={org_a['id']}")
    body = response.json()
    assert body["meta"]["total"] == 2
    assert {item["name"] for item in body["items"]} == {"Role A1", "Role A2"}


def test_delete_role(client: TestClient) -> None:
    org = create_organization(client)
    role = create_role(client, org["id"])

    response = client.delete(f"/api/v1/roles/{role['id']}")
    assert response.status_code == 204

    response = client.get(f"/api/v1/roles/{role['id']}")
    assert response.status_code == 404