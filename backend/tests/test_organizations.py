"""Organization tests (Phase 6.3: tenant-scoped, no creation via API).

Organization creation was removed from the API: the single seeded
organization is a tenant-context resource. Listing and detail access expose
only the authenticated user's own organization.
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi.testclient import TestClient

from app.models.organization import Organization

from tests.conftest import create_organization


def run_async(coro) -> Any:
    return asyncio.run(coro)


def test_list_organizations_returns_only_own(client: TestClient) -> None:
    """The organization list contains exactly the caller's own organization."""
    response = client.get("/api/v1/organizations")
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total"] == 1
    assert body["items"][0]["name"] == "Default Organization"


def test_get_own_organization(client: TestClient) -> None:
    org = create_organization(client)
    response = client.get(f"/api/v1/organizations/{org['id']}")
    assert response.status_code == 200
    assert response.json()["name"] == org["name"]


def test_get_foreign_organization_returns_404(client: TestClient) -> None:
    """Another tenant's organization is indistinguishable from a missing one."""
    foreign = run_async(
        Organization(name="Other Org", industry="Technology").insert()
    )
    assert foreign.id is not None
    response = client.get(f"/api/v1/organizations/{foreign.id}")
    assert response.status_code == 404


def test_get_missing_organization_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/organizations/507f1f77bcf86cd799439011")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "organization_not_found"


def test_organization_creation_removed_from_api(client: TestClient) -> None:
    """POST /organizations no longer exists (provisioning belongs to later phases).

    FastAPI answers 405 when the path exists with other methods, or 404 if
    the path itself is gone; either confirms creation is not exposed.
    """
    response = client.post(
        "/api/v1/organizations",
        json={"name": "Initech", "industry": "Technology"},
    )
    assert response.status_code in (404, 405)