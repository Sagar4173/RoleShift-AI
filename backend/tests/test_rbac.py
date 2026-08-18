"""Phase 6.4 RBAC authorization tests.

Covers the complete endpoint x role matrix against a real HTTP app
(mongomock backend, mocked AI provider): reads for every role, mutations
gated by ANALYST+, destructive/AI-spend actions gated by ADMIN+, owner
invariants, privilege-escalation prevention, cross-tenant membership
isolation, first-user-OWNER registration, and 404-before-403 ordering.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from beanie import PydanticObjectId
from fastapi.testclient import TestClient

from app.models.enums import MemberRole
from app.models.organization import Organization
from app.models.organization_membership import OrganizationMembership
from app.models.role import Role
from app.models.skill import Skill
from app.models.user import User
from app.core.exceptions import AppError, ConflictError
from app.repositories.membership import MembershipRepository
from app.services.membership_service import MembershipService

from tests.conftest import create_role, create_role_with_context
from tests.test_analysis import MOCK_AI_RESULT

PASSWORD = "Str0ng!Password"


def run_async(coro) -> Any:
    return asyncio.run(coro)


def _register(client: TestClient, email: str) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "display_name": email.split("@")[0].title(),
            "password": PASSWORD,
        },
    )
    assert response.status_code == 201, response.text


def _user_id(email: str) -> PydanticObjectId:
    user = run_async(User.find_one(User.email == email))
    assert user is not None and user.id is not None
    return user.id


def _promote(email: str, role: MemberRole) -> None:
    """Test-setup helper: set a user's membership role directly in the DB.

    This only works because registration itself creates the membership;
    a missing membership here is a real failure of the registration flow.
    """
    membership = run_async(
        OrganizationMembership.find_one(OrganizationMembership.user_id == _user_id(email))
    )
    assert membership is not None, "registration must create an organization membership"
    run_async(membership.set({OrganizationMembership.role: role}))


def _membership_count(organization_id: PydanticObjectId) -> int:
    return run_async(
        OrganizationMembership.find(OrganizationMembership.organization_id == organization_id).count()
    )


@pytest.fixture
def rbac_users(anon_client: TestClient) -> Iterator[dict[str, TestClient]]:
    """Four authenticated clients: owner, admin, analyst, viewer (one org).

    Registration assigns the first user OWNER and the rest VIEWER; the
    fixture then promotes admin/analyst directly in the DB (setup only —
    the API-driven role change is tested separately).
    """
    app = anon_client.app
    clients = {role: TestClient(app) for role in ("owner", "admin", "analyst", "viewer")}
    try:
        _register(clients["owner"], "owner@rbac.local")
        _register(clients["admin"], "admin@rbac.local")
        _register(clients["analyst"], "analyst@rbac.local")
        _register(clients["viewer"], "viewer@rbac.local")
        _promote("admin@rbac.local", MemberRole.ADMIN)
        _promote("analyst@rbac.local", MemberRole.ANALYST)
        yield clients
    finally:
        for client in clients.values():
            client.close()


def _org_id(client: TestClient) -> str:
    response = client.get("/api/v1/organizations")
    assert response.status_code == 200, response.text
    return response.json()["items"][0]["id"]


# ---------------------------------------------------------- registration


def test_first_registered_user_becomes_owner(anon_client: TestClient) -> None:
    _register(anon_client, "first@rbac.local")
    response = anon_client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["role"] == "owner"


def test_subsequent_registered_users_become_viewer(anon_client: TestClient) -> None:
    _register(anon_client, "first@rbac.local")
    second = TestClient(anon_client.app)
    try:
        _register(second, "second@rbac.local")
        response = second.get("/api/v1/auth/me")
        assert response.status_code == 200
        assert response.json()["role"] == "viewer"
    finally:
        second.close()


def test_registration_role_assignment_is_idempotent(anon_client: TestClient) -> None:
    _register(anon_client, "first@rbac.local")
    org_id = PydanticObjectId(_org_id(anon_client))
    assert _membership_count(org_id) == 1

    duplicate = anon_client.post(
        "/api/v1/auth/register",
        json={
            "email": "first@rbac.local",
            "display_name": "Duplicate",
            "password": PASSWORD,
        },
    )
    assert duplicate.status_code == 409
    assert _membership_count(org_id) == 1


def test_me_returns_role_for_each_role(rbac_users: dict[str, TestClient]) -> None:
    for role, client in rbac_users.items():
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 200, role
        assert response.json()["role"] == role, role


# ---------------------------------------------------------- reads (all roles)


READ_ENDPOINTS = [
    ("GET", "/api/v1/dashboard/summary", None),
    ("GET", "/api/v1/dashboard/skills", None),
    ("GET", "/api/v1/roles", None),
    ("GET", "/api/v1/roles/{role_id}", "role_id"),
    ("GET", "/api/v1/roles/{role_id}/analysis", "role_id"),
    ("GET", "/api/v1/roles/compare?role_ids={role_id}", "role_id"),
    ("GET", "/api/v1/processes", None),
    ("GET", "/api/v1/processes/{process_id}", "process_id"),
    ("GET", "/api/v1/activities", None),
    ("GET", "/api/v1/skills", None),
    ("GET", "/api/v1/organizations", None),
    ("GET", "/api/v1/organizations/{org_id}", "org_id"),
]


def test_reads_available_to_all_roles(
    rbac_users: dict[str, TestClient],
) -> None:
    owner = rbac_users["owner"]
    org_id = _org_id(owner)
    role = create_role(owner, org_id, name="Readable Role")
    process = owner.post(
        "/api/v1/processes",
        json={"name": "Readable Process", "description": "d"},
    ).json()

    for role_name, client in rbac_users.items():
        for method, path, param in READ_ENDPOINTS:
            url = path.format(
                role_id=role["id"],
                process_id=process["id"],
                org_id=org_id,
            )
            response = client.request(method, url)
            assert response.status_code == 200, f"{role_name}: {method} {url} -> {response.status_code}"


# ---------------------------------------------------------- mutations


def _role_payload(name: str) -> dict:
    return {"name": name, "industry": "Technology"}


def test_viewer_mutations_rejected(rbac_users: dict[str, TestClient]) -> None:
    owner, viewer = rbac_users["owner"], rbac_users["viewer"]
    org_id = _org_id(owner)
    role = create_role(owner, org_id, name="Target Role")
    process = owner.post(
        "/api/v1/processes",
        json={"name": "Target Process", "description": "d"},
    ).json()

    cases = [
        ("POST", "/api/v1/roles", _role_payload("Viewer Role")),
        ("PUT", f"/api/v1/roles/{role['id']}/current-skills", {"skills": ["Data Analysis"]}),
        ("DELETE", f"/api/v1/roles/{role['id']}", None),
        ("POST", "/api/v1/processes", {"name": "Viewer Process", "description": "d"}),
        (
            "POST",
            "/api/v1/activities",
            {
                "process_id": process["id"],
                "role_id": role["id"],
                "name": "Viewer Activity",
                "sequence": 1,
            },
        ),
        ("POST", "/api/v1/skills", {"name": "Viewer Skill"}),
    ]
    for method, path, body in cases:
        response = viewer.request(method, path, json=body)
        assert response.status_code == 403, f"viewer {method} {path} -> {response.status_code}"
        assert response.json()["detail"]["code"] == "insufficient_permissions"


def test_analyst_mutations_allowed_content_only(
    rbac_users: dict[str, TestClient],
) -> None:
    owner, analyst = rbac_users["owner"], rbac_users["analyst"]
    org_id = _org_id(owner)
    role = create_role(owner, org_id, name="Analyst Target")
    catalogue_skill = owner.post("/api/v1/skills", json={"name": "Data Analysis"})
    assert catalogue_skill.status_code == 201

    created = analyst.post("/api/v1/roles", json=_role_payload("Analyst Role"))
    assert created.status_code == 201
    analyst_role_id = created.json()["id"]

    skills = analyst.put(
        f"/api/v1/roles/{role['id']}/current-skills",
        json={"skills": ["Data Analysis"]},
    )
    assert skills.status_code == 200

    process = analyst.post("/api/v1/processes", json={"name": "Analyst Process", "description": "d"})
    assert process.status_code == 201
    activity = analyst.post(
        "/api/v1/activities",
        json={
            "process_id": process.json()["id"],
            "role_id": analyst_role_id,
            "name": "Analyst Activity",
            "sequence": 1,
        },
    )
    assert activity.status_code == 201

    assert analyst.delete(f"/api/v1/roles/{analyst_role_id}").status_code == 403
    assert analyst.post("/api/v1/skills", json={"name": "Analyst Skill"}).status_code == 403


def test_admin_destructive_actions_allowed(
    rbac_users: dict[str, TestClient],
) -> None:
    owner, admin = rbac_users["owner"], rbac_users["admin"]
    org_id = _org_id(owner)
    role = create_role(owner, org_id, name="Admin Target")

    assert admin.delete(f"/api/v1/roles/{role['id']}").status_code == 204
    assert admin.get(f"/api/v1/roles/{role['id']}").status_code == 404
    assert admin.post("/api/v1/skills", json={"name": "Admin Skill"}).status_code == 201


def test_owner_destructive_actions_allowed(rbac_users: dict[str, TestClient]) -> None:
    owner = rbac_users["owner"]
    org_id = _org_id(owner)
    role = create_role(owner, org_id, name="Owner Target")

    assert owner.delete(f"/api/v1/roles/{role['id']}").status_code == 204
    assert owner.post("/api/v1/skills", json={"name": "Owner Skill"}).status_code == 201


# ---------------------------------------------------------- AI permissions


def test_analyze_requires_analyst_or_above(rbac_users: dict[str, TestClient]) -> None:
    owner = rbac_users["owner"]
    org_id = _org_id(owner)
    roles = {
        role_name: create_role_with_context(owner, org_id, name=f"AI {role_name.title()}")
        for role_name in ("viewer", "analyst", "admin", "owner")
    }

    provider = AsyncMock()
    provider.name = "mock-provider"
    provider.analyze_role.return_value = MOCK_AI_RESULT

    with patch("app.services.analysis_service.get_provider", return_value=provider):
        viewer_response = rbac_users["viewer"].post(f"/api/v1/roles/{roles['viewer']['id']}/analyze")
        assert viewer_response.status_code == 403
        assert provider.analyze_role.call_count == 0

        for role_name in ("analyst", "admin", "owner"):
            response = rbac_users[role_name].post(f"/api/v1/roles/{roles[role_name]['id']}/analyze")
            assert response.status_code == 200, role_name
            assert response.json()["organization_id"] == org_id

    assert provider.analyze_role.call_count == 3


def test_force_reanalysis_requires_admin_or_owner(rbac_users: dict[str, TestClient]) -> None:
    owner = rbac_users["owner"]
    org_id = _org_id(owner)
    analyst_role = create_role_with_context(owner, org_id, name="Force Analyst")
    admin_role = create_role_with_context(owner, org_id, name="Force Admin")

    provider = AsyncMock()
    provider.name = "mock-provider"
    provider.analyze_role.return_value = MOCK_AI_RESULT

    with patch("app.services.analysis_service.get_provider", return_value=provider):
        analyst_force = rbac_users["analyst"].post(
            f"/api/v1/roles/{analyst_role['id']}/analyze",
            json={"force": True},
        )
        assert analyst_force.status_code == 403
        assert analyst_force.json()["detail"]["code"] == "insufficient_permissions"
        assert provider.analyze_role.call_count == 0

        admin_force = rbac_users["admin"].post(
            f"/api/v1/roles/{admin_role['id']}/analyze",
            json={"force": True},
        )
        assert admin_force.status_code == 200
        assert provider.analyze_role.call_count == 1


def test_analyze_new_requires_analyst_or_above(rbac_users: dict[str, TestClient]) -> None:
    owner = rbac_users["owner"]
    org_id = _org_id(owner)
    catalogue_skill = owner.post("/api/v1/skills", json={"name": "Data Analysis"})
    assert catalogue_skill.status_code == 201
    payload = {
        "name": "Analyze New Role",
        "industry": "Technology",
        "processes": [{"name": "Data Processing", "activities": ["Data Collection"]}],
        "current_skills": ["Data Analysis"],
    }

    provider = AsyncMock()
    provider.name = "mock-provider"
    provider.analyze_role.return_value = MOCK_AI_RESULT

    with patch("app.services.analysis_service.get_provider", return_value=provider):
        viewer_response = rbac_users["viewer"].post("/api/v1/roles/analyze-new", json=payload)
        assert viewer_response.status_code == 403
        assert provider.analyze_role.call_count == 0

        analyst_response = rbac_users["analyst"].post("/api/v1/roles/analyze-new", json=payload)
        assert analyst_response.status_code == 201
        assert analyst_response.json()["role"]["organization_id"] == org_id
        assert provider.analyze_role.call_count == 1


# ---------------------------------------------------------- member management


def test_members_list_requires_admin_or_owner(rbac_users: dict[str, TestClient]) -> None:
    assert rbac_users["owner"].get("/api/v1/organizations/members").status_code == 200
    assert rbac_users["admin"].get("/api/v1/organizations/members").status_code == 200
    assert rbac_users["analyst"].get("/api/v1/organizations/members").status_code == 403
    assert rbac_users["viewer"].get("/api/v1/organizations/members").status_code == 403


def test_members_list_contains_only_own_org_members(rbac_users: dict[str, TestClient]) -> None:
    owner = rbac_users["owner"]
    response = owner.get("/api/v1/organizations/members")
    assert response.status_code == 200
    members = response.json()["items"]
    emails = {member["email"] for member in members}
    assert emails == {"owner@rbac.local", "admin@rbac.local", "analyst@rbac.local", "viewer@rbac.local"}
    by_email = {member["email"]: member for member in members}
    assert by_email["owner@rbac.local"]["role"] == "owner"
    assert by_email["admin@rbac.local"]["role"] == "admin"
    assert by_email["analyst@rbac.local"]["role"] == "analyst"
    assert by_email["viewer@rbac.local"]["role"] == "viewer"


def test_admin_can_promote_and_demote_analyst_viewer(rbac_users: dict[str, TestClient]) -> None:
    admin, analyst, viewer = rbac_users["admin"], rbac_users["analyst"], rbac_users["viewer"]

    response = admin.put(
        f"/api/v1/organizations/members/{_user_id('viewer@rbac.local')}",
        json={"role": "analyst"},
    )
    assert response.status_code == 200
    assert response.json()["role"] == "analyst"
    assert viewer.get("/api/v1/auth/me").json()["role"] == "analyst"

    response = admin.put(
        f"/api/v1/organizations/members/{_user_id('analyst@rbac.local')}",
        json={"role": "viewer"},
    )
    assert response.status_code == 200
    assert analyst.get("/api/v1/auth/me").json()["role"] == "viewer"


def test_admin_cannot_set_owner_or_admin_roles(rbac_users: dict[str, TestClient]) -> None:
    admin = rbac_users["admin"]
    viewer_id = _user_id("viewer@rbac.local")
    admin_id = _user_id("admin@rbac.local")

    escalation = admin.put(f"/api/v1/organizations/members/{viewer_id}", json={"role": "owner"})
    assert escalation.status_code == 403

    promotion = admin.put(f"/api/v1/organizations/members/{viewer_id}", json={"role": "admin"})
    assert promotion.status_code == 403

    self_change = admin.put(f"/api/v1/organizations/members/{admin_id}", json={"role": "viewer"})
    assert self_change.status_code == 403


def test_admin_cannot_modify_owner(rbac_users: dict[str, TestClient]) -> None:
    admin = rbac_users["admin"]
    owner_id = _user_id("owner@rbac.local")

    demotion = admin.put(f"/api/v1/organizations/members/{owner_id}", json={"role": "viewer"})
    assert demotion.status_code == 403

    removal = admin.delete(f"/api/v1/organizations/members/{owner_id}")
    assert removal.status_code == 403


def test_owner_cannot_demote_or_remove_last_owner(rbac_users: dict[str, TestClient]) -> None:
    owner = rbac_users["owner"]
    owner_id = _user_id("owner@rbac.local")

    demotion = owner.put(f"/api/v1/organizations/members/{owner_id}", json={"role": "viewer"})
    assert demotion.status_code == 409
    assert demotion.json()["detail"]["code"] == "last_owner"

    removal = owner.delete(f"/api/v1/organizations/members/{owner_id}")
    assert removal.status_code == 409

    assert owner.get("/api/v1/auth/me").json()["role"] == "owner"


def test_owner_can_hand_over_and_then_leave(rbac_users: dict[str, TestClient]) -> None:
    owner = rbac_users["owner"]
    viewer = rbac_users["viewer"]
    owner_id = _user_id("owner@rbac.local")
    viewer_id = _user_id("viewer@rbac.local")

    handover = owner.put(f"/api/v1/organizations/members/{viewer_id}", json={"role": "owner"})
    assert handover.status_code == 200

    demotion = owner.put(f"/api/v1/organizations/members/{owner_id}", json={"role": "analyst"})
    assert demotion.status_code == 200
    assert owner.get("/api/v1/auth/me").json()["role"] == "analyst"

    # The former owner no longer holds member management, so the new owner
    # removes them (the only way a demoted owner can leave).
    assert owner.delete(f"/api/v1/organizations/members/{owner_id}").status_code == 403
    removal = viewer.delete(f"/api/v1/organizations/members/{owner_id}")
    assert removal.status_code == 204
    assert owner.get("/api/v1/auth/me").status_code == 401


def test_viewer_and_analyst_cannot_manage_members(rbac_users: dict[str, TestClient]) -> None:
    analyst, viewer = rbac_users["analyst"], rbac_users["viewer"]
    analyst_id = _user_id("analyst@rbac.local")
    viewer_id = _user_id("viewer@rbac.local")

    for client, actor in ((viewer, "viewer"), (analyst, "analyst")):
        change = client.put(f"/api/v1/organizations/members/{viewer_id}", json={"role": "analyst"})
        assert change.status_code == 403, actor
        removal = client.delete(f"/api/v1/organizations/members/{analyst_id}")
        assert removal.status_code == 403, actor


def test_removed_member_sessions_revoked(rbac_users: dict[str, TestClient]) -> None:
    admin, viewer = rbac_users["admin"], rbac_users["viewer"]
    assert viewer.get("/api/v1/auth/me").status_code == 200

    removal = admin.delete(f"/api/v1/organizations/members/{_user_id('viewer@rbac.local')}")
    assert removal.status_code == 204

    assert viewer.get("/api/v1/auth/me").status_code == 401


def test_members_endpoints_require_authentication(anon_client: TestClient) -> None:
    assert anon_client.get("/api/v1/organizations/members").status_code == 401
    assert anon_client.put(
        "/api/v1/organizations/members/507f1f77bcf86cd799439011",
        json={"role": "viewer"},
    ).status_code == 401
    assert anon_client.delete(
        "/api/v1/organizations/members/507f1f77bcf86cd799439011"
    ).status_code == 401


# ---------------------------------------------------------- cross-tenant


@pytest.fixture
def rbac_two_orgs(anon_client: TestClient) -> Iterator[tuple[TestClient, TestClient]]:
    """(owner of org A, bob as OWNER of org B) with memberships moved."""
    app = anon_client.app
    alice = TestClient(app)
    bob = TestClient(app)
    try:
        _register(alice, "alice@rbac.local")
        _register(bob, "bob@rbac.local")

        org_a = run_async(Organization.find_one(Organization.name == "Default Organization"))
        assert org_a is not None and org_a.id is not None
        bob_membership = run_async(
            OrganizationMembership.find_one(
                OrganizationMembership.user_id == _user_id("bob@rbac.local")
            )
        )
        assert bob_membership is not None

        org_b = run_async(Organization(name="RBAC Org B", industry="Technology").insert())
        assert org_b.id is not None

        run_async(bob_membership.set({OrganizationMembership.organization_id: org_b.id}))
        run_async(bob_membership.set({OrganizationMembership.role: MemberRole.OWNER}))
        run_async(User.find_one(User.email == "bob@rbac.local").set({User.organization_id: org_b.id}))

        assert _membership_count(org_a.id) == 1
        assert _membership_count(org_b.id) == 1
        yield alice, bob
    finally:
        alice.close()
        bob.close()


def test_cross_tenant_member_operations_are_404(rbac_two_orgs) -> None:
    alice, bob = rbac_two_orgs
    bob_id = _user_id("bob@rbac.local")
    alice_id = _user_id("alice@rbac.local")

    change = alice.put(f"/api/v1/organizations/members/{bob_id}", json={"role": "viewer"})
    assert change.status_code == 404

    removal = alice.delete(f"/api/v1/organizations/members/{bob_id}")
    assert removal.status_code == 404

    bob_change = bob.put(f"/api/v1/organizations/members/{alice_id}", json={"role": "viewer"})
    assert bob_change.status_code == 404


def test_cross_tenant_member_lists_are_scoped(rbac_two_orgs) -> None:
    alice, bob = rbac_two_orgs
    alice_members = alice.get("/api/v1/organizations/members").json()["items"]
    bob_members = bob.get("/api/v1/organizations/members").json()["items"]

    assert {m["email"] for m in alice_members} == {"alice@rbac.local"}
    assert {m["email"] for m in bob_members} == {"bob@rbac.local"}


def test_foreign_resource_404_before_permission_403(rbac_two_orgs) -> None:
    """Tenant scoping wins over RBAC: foreign resources are 404s, not 403s."""
    alice, bob = rbac_two_orgs
    alice_role = create_role(alice, _org_id(alice), name="Alice Role")
    bob_role = create_role(bob, _org_id(bob), name="Bob Role")

    for client in (alice, bob):
        foreign = bob_role["id"] if client is alice else alice_role["id"]
        response = client.get(f"/api/v1/roles/{foreign}")
        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "role_not_found"

    delete_foreign = bob.delete(f"/api/v1/roles/{alice_role['id']}")
    assert delete_foreign.status_code == 404


# ------------------------------------------- review-fix regression coverage


def test_concurrent_last_owner_demotions_keep_one_owner(
    rbac_users: dict[str, TestClient],
) -> None:
    """Two owners demoting each other concurrently cannot reach zero owners."""
    _promote("admin@rbac.local", MemberRole.OWNER)
    owner_id = _user_id("owner@rbac.local")
    admin_id = _user_id("admin@rbac.local")
    org_id = PydanticObjectId(_org_id(rbac_users["owner"]))

    service = MembershipService()
    owner_membership = run_async(service.get_for_user_in_org(owner_id, org_id))
    admin_membership = run_async(service.get_for_user_in_org(admin_id, org_id))
    assert owner_membership is not None and admin_membership is not None

    async def demote(actor, target_id) -> str:
        try:
            await service.change_role(
                actor=actor,
                organization_id=org_id,
                target_user_id=target_id,
                new_role=MemberRole.VIEWER,
            )
            return "ok"
        except ConflictError:
            return "conflict"

    async def run_races() -> tuple[str, str]:
        return await asyncio.gather(
            demote(owner_membership, admin_id),
            demote(admin_membership, owner_id),
        )

    results = run_async(run_races())
    assert sorted(results) == ["conflict", "ok"]
    assert run_async(MembershipRepository().count_owners(org_id)) == 1


def test_service_rejects_non_manager_actor(rbac_users: dict[str, TestClient]) -> None:
    """Defense in depth: MembershipService refuses VIEWER/ANALYST actors."""
    org_id = PydanticObjectId(_org_id(rbac_users["viewer"]))
    service = MembershipService()
    viewer_membership = run_async(
        service.get_for_user_in_org(_user_id("viewer@rbac.local"), org_id)
    )
    assert viewer_membership is not None
    with pytest.raises(AppError) as excinfo:
        run_async(
            service.change_role(
                actor=viewer_membership,
                organization_id=org_id,
                target_user_id=_user_id("owner@rbac.local"),
                new_role=MemberRole.VIEWER,
            )
        )
    assert excinfo.value.status_code == 403
    with pytest.raises(AppError) as excinfo:
        run_async(
            service.remove_member(
                actor=viewer_membership,
                organization_id=org_id,
                target_user_id=_user_id("owner@rbac.local"),
            )
        )
    assert excinfo.value.status_code == 403


def test_admin_cannot_remove_self(rbac_users: dict[str, TestClient]) -> None:
    """An admin may never remove or change an admin (incl. self)."""
    admin = rbac_users["admin"]
    admin_id = _user_id("admin@rbac.local")

    remove = admin.delete(f"/api/v1/organizations/members/{admin_id}")
    assert remove.status_code == 403
    assert remove.json()["detail"]["code"] == "insufficient_permissions"

    demote = admin.put(f"/api/v1/organizations/members/{admin_id}", json={"role": "viewer"})
    assert demote.status_code == 403

    assert _membership_count(PydanticObjectId(_org_id(admin))) == 4


def test_owner_self_removal_allowed_with_second_owner(
    rbac_users: dict[str, TestClient],
) -> None:
    """With 2+ owners, an owner may remove themselves; sessions are revoked."""
    _promote("admin@rbac.local", MemberRole.OWNER)
    owner = rbac_users["owner"]
    owner_id = _user_id("owner@rbac.local")
    org_id = PydanticObjectId(_org_id(owner))

    remove = owner.delete(f"/api/v1/organizations/members/{owner_id}")
    assert remove.status_code == 204

    assert _membership_count(org_id) == 3
    assert run_async(MembershipRepository().count_owners(org_id)) == 1
    assert run_async(User.get(owner_id)).organization_id is None
    assert owner.get("/api/v1/auth/me").status_code == 401


def test_removed_member_relogin_has_no_org_access(rbac_users: dict[str, TestClient]) -> None:
    """A removed member who logs in again has role null and no org access."""
    owner = rbac_users["owner"]
    viewer = rbac_users["viewer"]
    viewer_id = _user_id("viewer@rbac.local")

    assert owner.delete(f"/api/v1/organizations/members/{viewer_id}").status_code == 204

    relogin = viewer.post(
        "/api/v1/auth/login",
        json={"email": "viewer@rbac.local", "password": PASSWORD},
    )
    assert relogin.status_code == 200
    me = viewer.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["role"] is None

    roles = viewer.get("/api/v1/roles")
    assert roles.status_code == 403
    assert roles.json()["detail"]["code"] == "organization_required"


def test_analyze_new_rejects_force_field(anon_client: TestClient) -> None:
    """analyze-new must not accept a force field (force is ADMIN+ only)."""
    _register(anon_client, "first@rbac.local")
    response = anon_client.post(
        "/api/v1/roles/analyze-new",
        json={
            "name": "Forged Role",
            "industry": "Technology",
            "processes": [{"name": "Process", "activities": ["Act"]}],
            "current_skills": ["Skill"],
            "force": True,
        },
    )
    assert response.status_code == 422


def test_member_roster_respects_pagination(rbac_users: dict[str, TestClient]) -> None:
    """skip/limit apply server-side; total reflects the full roster."""
    roster = rbac_users["owner"].get("/api/v1/organizations/members?limit=2")
    assert roster.status_code == 200
    payload = roster.json()
    assert payload["meta"]["total"] == 4
    assert len(payload["items"]) == 2

    page_two = rbac_users["owner"].get("/api/v1/organizations/members?skip=2&limit=2")
    assert page_two.status_code == 200
    page_two_payload = page_two.json()
    assert len(page_two_payload["items"]) == 2
    assert {m["email"] for m in payload["items"]} != {
        m["email"] for m in page_two_payload["items"]
    }


# ------------------------------------------- global skill catalogue RBAC


def _catalogue_skill_count() -> int:
    return run_async(Skill.find().count())


def _assert_no_catalogue_writes(before: int) -> None:
    """A failed request must leave the global catalogue count unchanged."""
    after = _catalogue_skill_count()
    assert after == before, f"catalogue changed: {before} -> {after}"
    names = run_async(Skill.find().to_list())
    assert all(skill.name != "Transient Skill" for skill in names)


def test_owner_creates_global_skill_via_current_skills(
    rbac_users: dict[str, TestClient],
) -> None:
    owner = rbac_users["owner"]
    org_id = _org_id(owner)
    role = create_role(owner, org_id, name="Owner Skill Role")
    before = _catalogue_skill_count()

    response = owner.put(
        f"/api/v1/roles/{role['id']}/current-skills",
        json={"skills": ["Transient Skill"]},
    )
    assert response.status_code == 200
    assert response.json()["id"] == role["id"]
    assert _catalogue_skill_count() == before + 1
    assert run_async(Skill.find_one(Skill.name == "Transient Skill")) is not None


def test_admin_creates_global_skill_via_current_skills(
    rbac_users: dict[str, TestClient],
) -> None:
    owner, admin = rbac_users["owner"], rbac_users["admin"]
    org_id = _org_id(owner)
    role = create_role(owner, org_id, name="Admin Skill Role")
    before = _catalogue_skill_count()

    response = admin.put(
        f"/api/v1/roles/{role['id']}/current-skills",
        json={"skills": ["Transient Skill"]},
    )
    assert response.status_code == 200
    assert _catalogue_skill_count() == before + 1
    assert run_async(Skill.find_one(Skill.name == "Transient Skill")) is not None


def test_owner_creates_global_skill_via_analyze_new(
    rbac_users: dict[str, TestClient],
) -> None:
    owner = rbac_users["owner"]
    org_id = _org_id(owner)
    before = _catalogue_skill_count()

    provider = AsyncMock()
    provider.name = "mock-provider"
    provider.analyze_role.return_value = MOCK_AI_RESULT
    with patch("app.services.analysis_service.get_provider", return_value=provider):
        response = owner.post(
            "/api/v1/roles/analyze-new",
            json={
                "name": "Owner Skill Analyzed",
                "industry": "Technology",
                "processes": [{"name": "Data Processing", "activities": ["Data Collection"]}],
                "current_skills": ["Transient Skill"],
            },
        )
    assert response.status_code == 201, response.text
    assert _catalogue_skill_count() == before + 1
    assert run_async(Skill.find_one(Skill.name == "Transient Skill")) is not None
    assert provider.analyze_role.call_count == 1


def test_admin_creates_global_skill_via_analyze_new(
    rbac_users: dict[str, TestClient],
) -> None:
    owner, admin = rbac_users["owner"], rbac_users["admin"]
    org_id = _org_id(owner)
    before = _catalogue_skill_count()

    provider = AsyncMock()
    provider.name = "mock-provider"
    provider.analyze_role.return_value = MOCK_AI_RESULT
    with patch("app.services.analysis_service.get_provider", return_value=provider):
        response = admin.post(
            "/api/v1/roles/analyze-new",
            json={
                "name": "Admin Skill Analyzed",
                "industry": "Technology",
                "processes": [{"name": "Data Processing", "activities": ["Data Collection"]}],
                "current_skills": ["Transient Skill"],
            },
        )
    assert response.status_code == 201, response.text
    assert _catalogue_skill_count() == before + 1
    assert run_async(Skill.find_one(Skill.name == "Transient Skill")) is not None
    assert provider.analyze_role.call_count == 1


def test_analyst_can_use_existing_global_skill(
    rbac_users: dict[str, TestClient],
) -> None:
    owner, analyst = rbac_users["owner"], rbac_users["analyst"]
    org_id = _org_id(owner)
    owner.post("/api/v1/skills", json={"name": "Data Analysis"})
    role = create_role(owner, org_id, name="Analyst Skill Use")
    before = _catalogue_skill_count()

    linked = analyst.put(
        f"/api/v1/roles/{role['id']}/current-skills",
        json={"skills": ["Data Analysis"]},
    )
    assert linked.status_code == 200
    assert _catalogue_skill_count() == before
    assert linked.json()["id"] == role["id"]


def test_analyst_cannot_create_skill_via_current_skills(
    rbac_users: dict[str, TestClient],
) -> None:
    owner, analyst = rbac_users["owner"], rbac_users["analyst"]
    org_id = _org_id(owner)
    role = create_role(owner, org_id, name="Analyst Skill Blocked")
    before = _catalogue_skill_count()

    response = analyst.put(
        f"/api/v1/roles/{role['id']}/current-skills",
        json={"skills": ["Transient Skill"]},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "skill_not_found_in_catalogue"
    _assert_no_catalogue_writes(before)

    role_doc = run_async(Role.get(PydanticObjectId(role["id"])))
    assert role_doc is not None and role_doc.current_skill_ids == []


def test_analyst_cannot_create_skill_via_analyze_new(
    rbac_users: dict[str, TestClient],
) -> None:
    owner, analyst = rbac_users["owner"], rbac_users["analyst"]
    org_id = _org_id(owner)
    before = _catalogue_skill_count()

    provider = AsyncMock()
    provider.name = "mock-provider"
    provider.analyze_role.return_value = MOCK_AI_RESULT
    with patch("app.services.analysis_service.get_provider", return_value=provider):
        response = analyst.post(
            "/api/v1/roles/analyze-new",
            json={
                "name": "Analyst Skill Forbidden",
                "industry": "Technology",
                "processes": [{"name": "Data Processing", "activities": ["Data Collection"]}],
                "current_skills": ["Transient Skill"],
            },
        )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "skill_not_found_in_catalogue"
    assert provider.analyze_role.call_count == 0
    _assert_no_catalogue_writes(before)