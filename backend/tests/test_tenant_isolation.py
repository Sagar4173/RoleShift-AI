"""Phase 6.3 tenant isolation tests.

A two-organization world (alice in org A, bob in org B, registered on the
same app/database) exercises the full IDOR matrix: foreign reads are 404s,
foreign writes are rejected, AI analysis of a foreign role never reaches the
provider, deduplication is organization-scoped, dashboards aggregate only
the caller's org, and registration binds users to the oldest organization
(failing safely with 503 when none exists).
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from beanie import PydanticObjectId
from fastapi.testclient import TestClient
from app.models.organization import Organization
from app.models.user import User

from tests.conftest import (
    add_current_skills,
    create_activity,
    create_organization,
    create_process,
    create_role,
    create_role_with_context,
)
from tests.test_analysis import MOCK_AI_RESULT


def run_async(coro) -> Any:
    return asyncio.run(coro)


def _register(client: TestClient, email: str) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "display_name": "Tenant User",
            "password": "Str0ng!Password",
        },
    )
    assert response.status_code == 201, response.text


def _org_by_name(name: str) -> PydanticObjectId:
    org = run_async(Organization.find_one(Organization.name == name))
    assert org is not None and org.id is not None
    return org.id


def _reassign_user(email: str, organization_id: PydanticObjectId) -> None:
    user = run_async(User.find_one(User.email == email))
    assert user is not None
    run_async(user.set({User.organization_id: organization_id}))


def test_registration_binds_to_oldest_organization(anon_client: TestClient) -> None:
    """A new user joins the oldest existing organization (deterministic)."""
    org_a = _org_by_name("Default Organization")
    run_async(Organization(name="Younger Org", industry="Technology").insert())
    _register(anon_client, "oldest@roleshift.local")
    response = anon_client.get("/api/v1/organizations")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == str(org_a)


def test_registration_fails_safely_without_organizations(anon_client: TestClient) -> None:
    """Zero organizations: registration aborts with 503 (nothing invented)."""
    run_async(Organization.find().delete())
    response = anon_client.post(
        "/api/v1/auth/register",
        json={
            "email": "noorg@roleshift.local",
            "display_name": "No Org",
            "password": "Str0ng!Password",
        },
    )
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "organization_unavailable"


def _make_two_org_clients(anon_client: TestClient) -> tuple[TestClient, TestClient]:
    """Return (alice, bob) clients: alice in org A, bob in org B.

    The app is shared with anon_client (already initialized, org A seeded).
    New TestClient instances are created without entering a context manager
    so the lifespan (which re-seeds the default organization) does not run.
    Bob is moved to org B by updating his user record directly in the DB.
    """
    app = anon_client.app
    alice = TestClient(app)
    bob = TestClient(app)

    run_async(Organization(name="Org B", industry="Technology").insert())
    _register(alice, "alice@roleshift.local")
    _register(bob, "bob@roleshift.local")

    org_a = _org_by_name("Default Organization")
    org_b = _org_by_name("Org B")
    assert org_a != org_b

    _reassign_user("bob@roleshift.local", org_b)

    assert _org_by_name("Default Organization") == org_a
    assert _org_by_name("Org B") == org_b
    return alice, bob


@pytest.fixture
def two_org_clients(anon_client: TestClient) -> Iterator[tuple[TestClient, TestClient]]:
    """alice (org A) and bob (org B) clients, closed after each test.

    The extra TestClients spawn their own portal threads; closing them in
    teardown keeps the process memory bounded (scrypt hashing during
    registration is sensitive to memory pressure on Windows).
    """
    alice, bob = _make_two_org_clients(anon_client)
    try:
        yield alice, bob
    finally:
        alice.close()
        bob.close()


def test_roles_isolated_between_organizations(two_org_clients) -> None:
    alice, bob = two_org_clients
    org_a = _org_by_name("Default Organization")
    org_b = _org_by_name("Org B")

    role_a = create_role(alice, str(org_a), name="Alpha Role")
    role_b = create_role(bob, str(org_b), name="Beta Role")

    assert alice.get(f"/api/v1/roles/{role_a['id']}").status_code == 200
    assert bob.get(f"/api/v1/roles/{role_b['id']}").status_code == 200
    assert bob.get(f"/api/v1/roles/{role_a['id']}").status_code == 404
    assert alice.get(f"/api/v1/roles/{role_b['id']}").status_code == 404

    alice_list = alice.get("/api/v1/roles").json()
    bob_list = bob.get("/api/v1/roles").json()
    assert {r["name"] for r in alice_list["items"]} == {"Alpha Role"}
    assert {r["name"] for r in bob_list["items"]} == {"Beta Role"}

    assert alice_list["items"][0]["organization_id"] == str(org_a)
    assert bob_list["items"][0]["organization_id"] == str(org_b)


def test_foreign_role_writes_rejected(two_org_clients) -> None:
    alice, bob = two_org_clients
    org_a = _org_by_name("Default Organization")
    role_a = create_role(alice, str(org_a), name="Alpha Role")

    response = bob.put(
        f"/api/v1/roles/{role_a['id']}/current-skills",
        json={"skills": ["Data Analysis"]},
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "role_not_found"

    response = bob.delete(f"/api/v1/roles/{role_a['id']}")
    assert response.status_code == 404


def test_processes_isolated_between_organizations(two_org_clients) -> None:
    alice, bob = two_org_clients
    org_a = _org_by_name("Default Organization")
    org_b = _org_by_name("Org B")

    proc_a = create_process(alice, str(org_a), name="Alpha Process")
    proc_b = create_process(bob, str(org_b), name="Beta Process")

    assert alice.get(f"/api/v1/processes/{proc_a['id']}").status_code == 200
    assert bob.get(f"/api/v1/processes/{proc_b['id']}").status_code == 200
    assert bob.get(f"/api/v1/processes/{proc_a['id']}").status_code == 404
    assert alice.get(f"/api/v1/processes/{proc_b['id']}").status_code == 404


def test_activity_creation_requires_same_org_parents(two_org_clients) -> None:
    alice, bob = two_org_clients
    org_a = _org_by_name("Default Organization")
    org_b = _org_by_name("Org B")

    role_a = create_role(alice, str(org_a), name="Alpha Role")
    proc_a = create_process(alice, str(org_a), name="Alpha Process")
    proc_b = create_process(bob, str(org_b), name="Beta Process")
    role_b = create_role(bob, str(org_b), name="Beta Role")

    # Cross-tenant activity on alice's role via bob's process: rejected.
    response = bob.post(
        "/api/v1/activities",
        json={
            "process_id": proc_b["id"],
            "role_id": role_a["id"],
            "name": "Sneaky Activity",
            "sequence": 1,
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "role_not_found"

    # Cross-tenant activity on bob's role via alice's process: rejected.
    response = bob.post(
        "/api/v1/activities",
        json={
            "process_id": proc_a["id"],
            "role_id": role_b["id"],
            "name": "Sneaky Activity",
            "sequence": 1,
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "process_not_found"

    # Same-org creation works and carries the caller's organization.
    activity = create_activity(bob, role_b["id"], proc_b["id"], "Legit Activity")
    assert activity["organization_id"] == str(org_b)


def test_analysis_reads_isolated(two_org_clients) -> None:
    alice, bob = two_org_clients
    org_a = _org_by_name("Default Organization")
    role_a = create_role(alice, str(org_a), name="Alpha Role")

    assert bob.get(f"/api/v1/roles/{role_a['id']}/analysis").status_code == 404
    assert alice.get(f"/api/v1/roles/{role_a['id']}/analysis").status_code == 200


def test_analyze_foreign_role_rejected_before_provider(two_org_clients) -> None:
    alice, bob = two_org_clients
    org_a = _org_by_name("Default Organization")
    role_a = create_role_with_context(alice, str(org_a), name="Alpha Role")

    provider = AsyncMock()
    provider.name = "mock-provider"
    provider.analyze_role.return_value = MOCK_AI_RESULT

    with patch("app.services.analysis_service.get_provider", return_value=provider):
        response = bob.post(f"/api/v1/roles/{role_a['id']}/analyze")
        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "role_not_found"
        provider.analyze_role.assert_not_called()

        response = alice.post(f"/api/v1/roles/{role_a['id']}/analyze")
        assert response.status_code == 200
        assert response.json()["organization_id"] == str(org_a)
        provider.analyze_role.assert_called_once()


def test_dedup_isolation_between_organizations(two_org_clients) -> None:
    """Identical contexts in different orgs must not share cached results."""
    alice, bob = two_org_clients
    org_a = _org_by_name("Default Organization")
    org_b = _org_by_name("Org B")

    role_a = create_role_with_context(alice, str(org_a), name="Data Analyst")
    role_b = create_role_with_context(bob, str(org_b), name="Data Analyst")

    provider = AsyncMock()
    provider.name = "mock-provider"
    provider.analyze_role.return_value = MOCK_AI_RESULT

    with patch("app.services.analysis_service.get_provider", return_value=provider):
        assert bob.post(f"/api/v1/roles/{role_b['id']}/analyze").status_code == 200
        assert provider.analyze_role.call_count == 1

        # Same input hash as bob's run, but a different organization:
        # the provider MUST be invoked again (no cross-tenant cache hit).
        assert alice.post(f"/api/v1/roles/{role_a['id']}/analyze").status_code == 200
        assert provider.analyze_role.call_count == 2

        # Re-analysis within alice's org is deduplicated.
        assert alice.post(f"/api/v1/roles/{role_a['id']}/analyze").status_code == 200
        assert provider.analyze_role.call_count == 2

    assert alice.get(f"/api/v1/roles/{role_a['id']}/analysis").json()["has_analysis"] is True
    assert bob.get(f"/api/v1/roles/{role_b['id']}/analysis").json()["has_analysis"] is True
    assert bob.get(f"/api/v1/roles/{role_a['id']}/analysis").status_code == 404


def test_dashboard_isolated_between_organizations(two_org_clients) -> None:
    alice, bob = two_org_clients
    org_a = _org_by_name("Default Organization")
    org_b = _org_by_name("Org B")

    role_a = create_role_with_context(alice, str(org_a), name="Alpha Role")
    create_role(alice, str(org_a), name="Second Alpha Role")
    create_role(bob, str(org_b), name="Beta Role")

    provider = AsyncMock()
    provider.name = "mock-provider"
    provider.analyze_role.return_value = MOCK_AI_RESULT
    with patch("app.services.analysis_service.get_provider", return_value=provider):
        assert alice.post(f"/api/v1/roles/{role_a['id']}/analyze").status_code == 200

    alice_summary = alice.get("/api/v1/dashboard/summary").json()
    bob_summary = bob.get("/api/v1/dashboard/summary").json()
    assert alice_summary["total_roles"] == 2
    assert bob_summary["total_roles"] == 1
    assert alice_summary["roles_analyzed"] == 1
    assert bob_summary["roles_analyzed"] == 0
    assert {r["role_name"] for r in alice_summary["recent_role_analyses"]} == {"Alpha Role"}
    assert bob_summary["recent_role_analyses"] == []
    assert {s["name"] for s in alice_summary["top_future_skills"]} == {"AI Prompt Engineering"}
    assert bob_summary["top_future_skills"] == []


def test_organizations_list_scoped_to_own_tenant(two_org_clients) -> None:
    alice, bob = two_org_clients
    org_a = _org_by_name("Default Organization")
    org_b = _org_by_name("Org B")

    assert alice.get("/api/v1/organizations").json()["items"][0]["id"] == str(org_a)
    assert bob.get("/api/v1/organizations").json()["items"][0]["id"] == str(org_b)

    # Foreign organization detail is a 404 (no existence oracle).
    assert alice.get(f"/api/v1/organizations/{org_b}").status_code == 404
    assert bob.get(f"/api/v1/organizations/{org_a}").status_code == 404