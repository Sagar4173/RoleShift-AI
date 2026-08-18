"""Phase 6.5.1: global skill catalogue concurrency regression tests.

Covers the concurrency blocker fix:

- rollback reference-check: a skill created by a failed analyze-new is
  deleted only when NO other persisted role (in ANY organization) references
  it; the failed request's own role never blocks cleanup;
- unique canonical-name index: exactly one catalogue document per
  normalized name, even under concurrent creation;
- race-safe get-or-create: a lost insert race recovers by re-reading the
  winner's document — never a fatal error, never a duplicate;
- only the request that actually inserted a skill records it in the
  CreationTracker;
- cross-organization references preserve the skill (skills stay global);
- normalization: case/whitespace variants resolve to the same catalogue
  entry.

All tests run against the in-memory database with a mocked AI provider —
no real LLM calls are made.
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
from app.services.ai.base import AIProviderUnavailableError
from app.repositories.skill import SkillRepository
from app.services.role_service import RoleService
from app.services.skill_service import SkillService
from app.schemas.skill import SkillCreate

from tests.test_analysis import MOCK_AI_RESULT

PASSWORD = "Str0ng!Password"

VALID_PAYLOAD = {
    "name": "Transactional Role",
    "industry": "Technology",
    "processes": [{"name": "Data Processing", "activities": ["Data Collection"]}],
    "current_skills": ["Shared Concurrency Skill"],
}


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
    membership = run_async(
        OrganizationMembership.find_one(OrganizationMembership.user_id == _user_id(email))
    )
    assert membership is not None, "registration must create an organization membership"
    run_async(membership.set({OrganizationMembership.role: role}))


@pytest.fixture
def rbac_users(anon_client: TestClient) -> Iterator[dict[str, TestClient]]:
    """owner + analyst + viewer clients in one organization."""
    app = anon_client.app
    clients = {name: TestClient(app) for name in ("owner", "analyst", "viewer")}
    try:
        _register(clients["owner"], "owner@skillcc.local")
        _register(clients["analyst"], "analyst@skillcc.local")
        _register(clients["viewer"], "viewer@skillcc.local")
        _promote("analyst@skillcc.local", MemberRole.ANALYST)
        yield clients
    finally:
        for client in clients.values():
            client.close()


@pytest.fixture
def two_orgs(anon_client: TestClient) -> Iterator[tuple[TestClient, TestClient]]:
    """(alice of org A, bob of org B) — mirrors the RBAC cross-tenant fixture."""
    app = anon_client.app
    alice = TestClient(app)
    bob = TestClient(app)
    try:
        _register(alice, "alice@skillcc.local")
        _register(bob, "bob@skillcc.local")

        org_a = run_async(Organization.find_one(Organization.name == "Default Organization"))
        assert org_a is not None and org_a.id is not None
        bob_membership = run_async(
            OrganizationMembership.find_one(
                OrganizationMembership.user_id == _user_id("bob@skillcc.local")
            )
        )
        assert bob_membership is not None

        org_b = run_async(Organization(name="SkillCC Org B", industry="Technology").insert())
        assert org_b.id is not None

        run_async(bob_membership.set({OrganizationMembership.organization_id: org_b.id}))
        run_async(bob_membership.set({OrganizationMembership.role: MemberRole.OWNER}))
        run_async(User.find_one(User.email == "bob@skillcc.local").set({User.organization_id: org_b.id}))
        yield alice, bob
    finally:
        alice.close()
        bob.close()


def _org_id(client: TestClient) -> str:
    response = client.get("/api/v1/organizations")
    assert response.status_code == 200, response.text
    return response.json()["items"][0]["id"]


def _skill_count() -> int:
    return run_async(Skill.find().count())


def _skill_by_name(name: str) -> Skill | None:
    return run_async(Skill.find_one(Skill.name == name))


def _create_empty_role(client: TestClient, org_id: str, name: str) -> dict:
    """A persisted role with no skills (a candidate "other role")."""
    response = client.post("/api/v1/roles", json={"name": name, "industry": "Technology"})
    assert response.status_code == 201, response.text
    return response.json()


async def _link_skill_to_role(role_id: str, org_id: str, skill_name: str) -> None:
    """Link a skill onto a persisted role at the service level (like a concurrent B).

    Runs inside the app's event loop (invoked from a provider side effect), so
    it is async and performs DB work directly.
    """
    role = await RoleService().set_current_skills(
        PydanticObjectId(role_id),
        [skill_name],
        PydanticObjectId(org_id),
        allow_skill_catalogue_create=False,
    )
    assert role.id is not None
    assert len(role.current_skill_ids) == 1


def _failing_provider_with_link(*, role_id: str, org_id: str, skill_name: str) -> AsyncMock:
    """Provider that links the skill to another role while "running", then fails."""
    provider = AsyncMock()
    provider.name = "deepseek"

    async def side_effect(request) -> None:
        await _link_skill_to_role(role_id, org_id, skill_name)
        raise AIProviderUnavailableError("down")

    provider.analyze_role.side_effect = side_effect
    return provider


# ------------------------------------------- rollback reference-check


def test_failed_request_deletes_unused_created_skill(
    rbac_users: dict[str, TestClient],
) -> None:
    """A failed analyze-new removes a skill no other role references."""
    owner = rbac_users["owner"]
    before = _skill_count()

    provider = AsyncMock()
    provider.name = "deepseek"
    provider.analyze_role.side_effect = AIProviderUnavailableError("down")
    with patch("app.services.analysis_service.get_provider", return_value=provider):
        response = owner.post("/api/v1/roles/analyze-new", json=VALID_PAYLOAD)
    assert response.status_code == 503

    assert _skill_count() == before
    assert _skill_by_name("Shared Concurrency Skill") is None
    assert run_async(Role.find().count()) == 0


def test_failed_request_preserves_skill_referenced_by_other_role(
    rbac_users: dict[str, TestClient],
) -> None:
    """Another role linking the skill during the provider call keeps it alive."""
    owner = rbac_users["owner"]
    org_id = _org_id(owner)
    other_role = _create_empty_role(owner, org_id, "Other Role")
    before = _skill_count()

    provider = _failing_provider_with_link(
        role_id=other_role["id"], org_id=org_id, skill_name="Shared Concurrency Skill"
    )
    with patch("app.services.analysis_service.get_provider", return_value=provider):
        response = owner.post("/api/v1/roles/analyze-new", json=VALID_PAYLOAD)
    assert response.status_code == 503

    assert _skill_count() == before + 1
    skill = _skill_by_name("Shared Concurrency Skill")
    assert skill is not None and skill.id is not None
    other = run_async(Role.get(PydanticObjectId(other_role["id"])))
    assert other is not None and skill.id in other.current_skill_ids


def test_failed_request_own_role_reference_does_not_block_deletion(
    rbac_users: dict[str, TestClient],
) -> None:
    """The doomed role's own reference must not keep the unused skill alive."""
    owner = rbac_users["owner"]
    before = _skill_count()

    provider = AsyncMock()
    provider.name = "deepseek"
    provider.analyze_role.side_effect = AIProviderUnavailableError("down")
    with patch("app.services.analysis_service.get_provider", return_value=provider):
        response = owner.post("/api/v1/roles/analyze-new", json=VALID_PAYLOAD)
    assert response.status_code == 503

    assert _skill_count() == before
    assert _skill_by_name("Shared Concurrency Skill") is None
    assert run_async(Role.find().count()) == 0


def test_pre_existing_skill_never_deleted_on_failure(
    rbac_users: dict[str, TestClient],
) -> None:
    """A skill that existed before the request is untouched by rollback."""
    owner = rbac_users["owner"]
    created = owner.post("/api/v1/skills", json={"name": "Data Analysis"})
    assert created.status_code == 201
    before = _skill_count()

    provider = AsyncMock()
    provider.name = "deepseek"
    provider.analyze_role.side_effect = AIProviderUnavailableError("down")
    payload = {**VALID_PAYLOAD, "current_skills": ["Data Analysis"]}
    with patch("app.services.analysis_service.get_provider", return_value=provider):
        response = owner.post("/api/v1/roles/analyze-new", json=payload)
    assert response.status_code == 503

    assert _skill_count() == before
    assert _skill_by_name("Data Analysis") is not None


def test_cross_organization_reference_preserves_skill(
    two_orgs: tuple[TestClient, TestClient],
) -> None:
    """The reference check is global: org B's role protects a skill created by org A."""
    alice, bob = two_orgs
    org_a = _org_id(alice)
    org_b = _org_id(bob)
    bob_role = _create_empty_role(bob, org_b, "Bob's Role")
    before = _skill_count()

    provider = _failing_provider_with_link(
        role_id=bob_role["id"], org_id=org_b, skill_name="Shared Concurrency Skill"
    )
    with patch("app.services.analysis_service.get_provider", return_value=provider):
        response = alice.post("/api/v1/roles/analyze-new", json=VALID_PAYLOAD)
    assert response.status_code == 503

    assert _skill_count() == before + 1
    skill = _skill_by_name("Shared Concurrency Skill")
    assert skill is not None and skill.id is not None
    bob_role_doc = run_async(Role.get(PydanticObjectId(bob_role["id"])))
    assert bob_role_doc is not None and skill.id in bob_role_doc.current_skill_ids


# ------------------------------------------- concurrent same-name creation


def test_concurrent_same_name_creation_yields_single_document(
    anon_client: TestClient,
) -> None:
    """Two concurrent get-or-create calls for the same name produce ONE Skill."""
    del anon_client
    skill_service = SkillService()
    created_a: list[Skill] = []
    created_b: list[Skill] = []

    async def create_a() -> Skill:
        return await skill_service.get_or_create_by_name(
            "Concurrent Brand New Skill", created=created_a
        )

    async def create_b() -> Skill:
        return await skill_service.get_or_create_by_name(
            "Concurrent Brand New Skill", created=created_b
        )

    async def run_both() -> tuple[Skill, Skill]:
        return await asyncio.gather(create_a(), create_b())

    result_a, result_b = run_async(run_both())

    assert result_a.id is not None and result_b.id is not None
    assert result_a.id == result_b.id
    assert _skill_count() == 1


def test_only_actual_inserting_request_records_in_tracker(
    anon_client: TestClient,
) -> None:
    """Exactly one of the racing callers records the skill on its tracker."""
    del anon_client
    skill_service = SkillService()
    created_a: list[Skill] = []
    created_b: list[Skill] = []

    async def create_a() -> Skill:
        return await skill_service.get_or_create_by_name(
            "Tracker Brand New Skill", created=created_a
        )

    async def create_b() -> Skill:
        return await skill_service.get_or_create_by_name(
            "Tracker Brand New Skill", created=created_b
        )

    async def run_both() -> None:
        await asyncio.gather(create_a(), create_b())

    run_async(run_both())

    assert _skill_count() == 1
    assert len(created_a) + len(created_b) == 1


def test_lost_insert_race_recovers_winner_without_error(
    anon_client: TestClient,
) -> None:
    """Duplicate-key on insert re-reads the winner: no error, no duplicate."""
    del anon_client
    service = SkillService()
    winner = run_async(service.create(SkillCreate(name="Data Analysis")))
    assert winner.id is not None
    before = _skill_count()

    real_get_by_normalized = SkillRepository.get_by_normalized_name
    calls = 0

    async def stale_first_lookup(self, name: str) -> Skill | None:
        nonlocal calls
        calls += 1
        if calls == 1:
            return None
        return await real_get_by_normalized(self, name)

    created: list[Skill] = []
    with patch.object(SkillRepository, "get_by_normalized_name", stale_first_lookup):
        loser = run_async(service.get_or_create_by_name("data analysis", created=created))

    assert calls >= 2
    assert loser.id == winner.id
    assert _skill_count() == before
    assert created == []


def test_case_variant_resolves_to_existing_catalogue_entry(
    rbac_users: dict[str, TestClient],
) -> None:
    """'data analysis' resolves to 'Data Analysis' — one catalogue entry."""
    owner, analyst = rbac_users["owner"], rbac_users["analyst"]
    assert owner.post("/api/v1/skills", json={"name": "Data Analysis"}).status_code == 201
    before = _skill_count()

    service = SkillService()
    resolved = run_async(service.get_or_create_by_name("data analysis"))
    assert resolved.name == "Data Analysis"
    assert _skill_count() == before

    role = _create_empty_role(owner, _org_id(owner), "Case Variant Role")
    linked = analyst.put(
        f"/api/v1/roles/{role['id']}/current-skills",
        json={"skills": ["data analysis"]},
    )
    assert linked.status_code == 200
    assert _skill_count() == before


# ------------------------------------------------- concurrent requester role


def test_failed_analyze_new_keeps_concurrent_requester_role_valid(
    rbac_users: dict[str, TestClient],
) -> None:
    """B's role stays valid (skill resolvable) after A's failed rollback."""
    owner = rbac_users["owner"]
    org_id = _org_id(owner)
    other_role = _create_empty_role(owner, org_id, "Concurrent Requester Role")

    provider = _failing_provider_with_link(
        role_id=other_role["id"], org_id=org_id, skill_name="Shared Concurrency Skill"
    )
    with patch("app.services.analysis_service.get_provider", return_value=provider):
        response = owner.post("/api/v1/roles/analyze-new", json=VALID_PAYLOAD)
    assert response.status_code == 503

    assert _skill_by_name("Shared Concurrency Skill") is not None
    assert owner.get(f"/api/v1/roles/{other_role['id']}").status_code == 200
    other = run_async(Role.get(PydanticObjectId(other_role["id"])))
    assert other is not None and len(other.current_skill_ids) == 1
    skill = _skill_by_name("Shared Concurrency Skill")
    assert skill is not None and skill.id == other.current_skill_ids[0]