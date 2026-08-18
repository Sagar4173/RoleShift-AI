"""Phase 6.5.1: analyze-new transactional integrity regression tests.

Proves that POST /api/v1/roles/analyze-new is atomic from the application's
perspective:

- request-level validation failures (context gate, unknown catalogue skill
  for ANALYST) leave ZERO created documents;
- a failure during creation, AI provider execution, or output validation
  rolls back every document the request created (role, processes,
  activities, newly created skills, RoleAnalysis, AnalysisRun);
- pre-existing resources are never deleted during rollback;
- compensation is tenant-scoped (another organization's data is untouched);
- a retry after a rolled-back failure succeeds and leaves exactly one set
  of documents.

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

from app.core.exceptions import DatabaseError
from app.models.analysis_run import AnalysisRun
from app.models.enums import MemberRole
from app.models.organization import Organization
from app.models.organization_membership import OrganizationMembership
from app.models.activity import Activity
from app.models.process import Process
from app.models.role import Role
from app.models.role_analysis import RoleAnalysis
from app.models.skill import Skill
from app.models.user import User
from app.services.ai.base import AIProviderUnavailableError
from app.services.activity_service import ActivityService

from tests.test_analysis import MOCK_AI_RESULT

PASSWORD = "Str0ng!Password"

VALID_PAYLOAD = {
    "name": "Transactional Role",
    "industry": "Technology",
    "processes": [{"name": "Data Processing", "activities": ["Data Collection"]}],
    "current_skills": ["Data Analysis"],
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
    """owner + analyst + viewer clients in one organization (API-driven setup)."""
    app = anon_client.app
    clients = {
        name: TestClient(app) for name in ("owner", "analyst", "viewer")
    }
    try:
        _register(clients["owner"], "owner@atomic.local")
        _register(clients["analyst"], "analyst@atomic.local")
        _register(clients["viewer"], "viewer@atomic.local")
        _promote("analyst@atomic.local", MemberRole.ANALYST)
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
        _register(alice, "alice@atomic.local")
        _register(bob, "bob@atomic.local")

        org_a = run_async(Organization.find_one(Organization.name == "Default Organization"))
        assert org_a is not None and org_a.id is not None
        bob_membership = run_async(
            OrganizationMembership.find_one(
                OrganizationMembership.user_id == _user_id("bob@atomic.local")
            )
        )
        assert bob_membership is not None

        org_b = run_async(Organization(name="Atomic Org B", industry="Technology").insert())
        assert org_b.id is not None

        run_async(bob_membership.set({OrganizationMembership.organization_id: org_b.id}))
        run_async(bob_membership.set({OrganizationMembership.role: MemberRole.OWNER}))
        run_async(User.find_one(User.email == "bob@atomic.local").set({User.organization_id: org_b.id}))
        yield alice, bob
    finally:
        alice.close()
        bob.close()


def _org_id(client: TestClient) -> str:
    response = client.get("/api/v1/organizations")
    assert response.status_code == 200, response.text
    return response.json()["items"][0]["id"]


def _provider(result: Any = MOCK_AI_RESULT) -> AsyncMock:
    provider = AsyncMock()
    provider.name = "deepseek"
    provider.analyze_role.return_value = result
    return provider


async def _counts() -> dict[str, int]:
    return {
        "roles": await Role.find().count(),
        "processes": await Process.find().count(),
        "activities": await Activity.find().count(),
        "analyses": await RoleAnalysis.find().count(),
        "runs": await AnalysisRun.find().count(),
        "skills": await Skill.find().count(),
    }


EMPTY_COUNTS = {"roles": 0, "processes": 0, "activities": 0, "analyses": 0, "runs": 0, "skills": 0}


# ------------------------------------------------- request-level validation


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "No Industry", "processes": [{"name": "P", "activities": ["A"]}], "current_skills": ["S"]},
        {"name": "No Activities", "industry": "Tech", "current_skills": ["S"]},
        {"name": "No Skills", "industry": "Tech", "processes": [{"name": "P", "activities": ["A"]}]},
        {"name": "Empty Activities", "industry": "Tech", "processes": [{"name": "P", "activities": []}], "current_skills": ["S"]},
        {"name": "No Processes", "industry": "Tech", "current_skills": ["S"]},
    ],
)
def test_context_gate_failure_leaves_zero_resources(
    rbac_users: dict[str, TestClient], payload: dict
) -> None:
    """A context-gate 422 happens BEFORE anything is persisted."""
    provider = _provider()
    with patch("app.services.analysis_service.get_provider", return_value=provider):
        response = rbac_users["owner"].post("/api/v1/roles/analyze-new", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "validation_error"
    provider.analyze_role.assert_not_called()
    assert run_async(_counts()) == EMPTY_COUNTS


def test_analyst_unknown_skill_failure_leaves_zero_resources(
    rbac_users: dict[str, TestClient],
) -> None:
    """ANALYST referencing a missing catalogue skill: 422 before any write."""
    before = run_async(_counts())
    provider = _provider()
    payload = {**VALID_PAYLOAD, "current_skills": ["Never In Catalogue"]}
    with patch("app.services.analysis_service.get_provider", return_value=provider):
        response = rbac_users["analyst"].post("/api/v1/roles/analyze-new", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "skill_not_found_in_catalogue"
    provider.analyze_role.assert_not_called()
    assert run_async(_counts()) == before


def test_viewer_forbidden_leaves_zero_resources(
    rbac_users: dict[str, TestClient],
) -> None:
    """A 403 permission rejection happens before anything is persisted."""
    provider = _provider()
    with patch("app.services.analysis_service.get_provider", return_value=provider):
        response = rbac_users["viewer"].post("/api/v1/roles/analyze-new", json=VALID_PAYLOAD)
    assert response.status_code == 403
    provider.analyze_role.assert_not_called()
    assert run_async(_counts()) == EMPTY_COUNTS


# ------------------------------------------------- downstream failure rollback


def test_provider_failure_rolls_back_everything_created(
    rbac_users: dict[str, TestClient],
) -> None:
    """AI provider failure: role, process, activity, and run are all removed.

    The run created for the attempt is deleted too — a failed analyze-new
    leaves no FAILED run and no orphaned role behind.
    """
    owner = rbac_users["owner"]
    owner.post("/api/v1/skills", json={"name": "Data Analysis"})
    before = run_async(_counts())

    provider = _provider()
    provider.analyze_role.side_effect = AIProviderUnavailableError("down")
    with patch("app.services.analysis_service.get_provider", return_value=provider):
        response = owner.post("/api/v1/roles/analyze-new", json=VALID_PAYLOAD)
    assert response.status_code == 503
    assert provider.analyze_role.call_count == 1
    assert run_async(_counts()) == before
    assert run_async(Skill.find_one(Skill.name == "Data Analysis")) is not None


def test_created_skill_is_rolled_back_on_provider_failure(
    rbac_users: dict[str, TestClient],
) -> None:
    """A catalogue skill created by the request is compensated on failure."""
    owner = rbac_users["owner"]
    before = run_async(_counts())

    provider = _provider()
    provider.analyze_role.side_effect = AIProviderUnavailableError("down")
    payload = {**VALID_PAYLOAD, "current_skills": ["Transient Skill"]}
    with patch("app.services.analysis_service.get_provider", return_value=provider):
        response = owner.post("/api/v1/roles/analyze-new", json=payload)
    assert response.status_code == 503
    assert run_async(_counts()) == before
    assert run_async(Skill.find_one(Skill.name == "Transient Skill")) is None


def test_output_validation_failure_rolls_back_everything_created(
    rbac_users: dict[str, TestClient],
) -> None:
    """Malformed provider output: no analysis, no run, no role remains."""
    owner = rbac_users["owner"]
    owner.post("/api/v1/skills", json={"name": "Data Analysis"})
    before = run_async(_counts())

    provider = _provider()
    provider.analyze_role.return_value = {"unexpected": "shape"}
    with patch("app.services.analysis_service.get_provider", return_value=provider):
        response = owner.post("/api/v1/roles/analyze-new", json=VALID_PAYLOAD)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "ai_output_validation_error"
    assert run_async(_counts()) == before


def test_downstream_creation_failure_rolls_back_everything_created(
    rbac_users: dict[str, TestClient],
) -> None:
    """A persistence failure mid-creation compensates every document so far.

    The role and its process exist when the first activity insert fails;
    compensation must remove them all.
    """
    owner = rbac_users["owner"]
    before = run_async(_counts())

    with patch.object(
        ActivityService,
        "create",
        AsyncMock(side_effect=DatabaseError("Failed to persist activity")),
    ):
        response = owner.post("/api/v1/roles/analyze-new", json=VALID_PAYLOAD)
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "database_unavailable"
    assert run_async(_counts()) == before


# ------------------------------------------- pre-existing resources preserved


def test_rollback_never_touches_pre_existing_resources(
    rbac_users: dict[str, TestClient],
) -> None:
    """A pre-existing role with analysis survives a failed analyze-new."""
    owner = rbac_users["owner"]
    org_id = _org_id(owner)
    existing = _create_role_with_analysis(owner, org_id, name="Existing Role")
    before = run_async(_counts())
    assert before["roles"] == 1 and before["analyses"] == 1 and before["runs"] == 1

    provider = _provider()
    provider.analyze_role.side_effect = AIProviderUnavailableError("down")
    with patch("app.services.analysis_service.get_provider", return_value=provider):
        response = owner.post("/api/v1/roles/analyze-new", json=VALID_PAYLOAD)
    assert response.status_code == 503

    assert run_async(_counts()) == before
    assert owner.get(f"/api/v1/roles/{existing['id']}").status_code == 200
    assert owner.get(f"/api/v1/roles/{existing['id']}/analysis").json()["has_analysis"] is True


def test_rollback_does_not_touch_other_organization(
    two_orgs: tuple[TestClient, TestClient],
) -> None:
    """Compensation is tenant-scoped: org B's data is untouched by org A's failure."""
    alice, bob = two_orgs
    bob_role = _create_role_with_analysis(bob, _org_id(bob), name="Bob's Role")
    bob_before = run_async(_counts())

    provider = _provider()
    provider.analyze_role.side_effect = AIProviderUnavailableError("down")
    with patch("app.services.analysis_service.get_provider", return_value=provider):
        response = alice.post("/api/v1/roles/analyze-new", json=VALID_PAYLOAD)
    assert response.status_code == 503

    assert run_async(_counts()) == bob_before
    assert bob.get(f"/api/v1/roles/{bob_role['id']}").status_code == 200
    assert bob.get(f"/api/v1/roles/{bob_role['id']}/analysis").json()["has_analysis"] is True


# ------------------------------------------------------- retry after failure


def test_retry_after_provider_failure_succeeds(
    rbac_users: dict[str, TestClient],
) -> None:
    """A rolled-back failure leaves a clean slate: retry persists exactly one set."""
    owner = rbac_users["owner"]
    provider = _provider()
    provider.analyze_role.side_effect = [AIProviderUnavailableError("down"), MOCK_AI_RESULT]

    with patch("app.services.analysis_service.get_provider", return_value=provider):
        first = owner.post("/api/v1/roles/analyze-new", json=VALID_PAYLOAD)
        assert first.status_code == 503
        second = owner.post("/api/v1/roles/analyze-new", json=VALID_PAYLOAD)
        assert second.status_code == 201, second.text

    assert provider.analyze_role.call_count == 2
    assert run_async(_counts()) == {
        "roles": 1,
        "processes": 1,
        "activities": 1,
        "analyses": 1,
        "runs": 1,
        "skills": 1,
    }


# ------------------------------------------------------------- success control


def test_success_keeps_everything_created(
    rbac_users: dict[str, TestClient],
) -> None:
    """Control: a successful analyze-new persists role, context, analysis, run."""
    owner = rbac_users["owner"]
    provider = _provider()
    with patch("app.services.analysis_service.get_provider", return_value=provider):
        response = owner.post("/api/v1/roles/analyze-new", json=VALID_PAYLOAD)
    assert response.status_code == 201, response.text
    assert run_async(_counts()) == {
        "roles": 1,
        "processes": 1,
        "activities": 1,
        "analyses": 1,
        "runs": 1,
        "skills": 1,
    }
    assert provider.analyze_role.call_count == 1


# ------------------------------------------------------------------ helpers


def _create_role_with_analysis(client: TestClient, org_id: str, *, name: str) -> dict:
    """Create a role with context and analyze it successfully (mocked provider)."""
    role = client.post(
        "/api/v1/roles",
        json={"name": name, "industry": "Technology"},
    )
    assert role.status_code == 201
    role_id = role.json()["id"]
    process = client.post("/api/v1/processes", json={"name": "Existing Process", "description": "d"})
    assert process.status_code == 201
    activity = client.post(
        "/api/v1/activities",
        json={
            "process_id": process.json()["id"],
            "role_id": role_id,
            "name": "Existing Activity",
            "sequence": 1,
        },
    )
    assert activity.status_code == 201
    skills = client.put(
        f"/api/v1/roles/{role_id}/current-skills",
        json={"skills": ["Data Analysis"]},
    )
    assert skills.status_code == 200

    provider = _provider()
    with patch("app.services.analysis_service.get_provider", return_value=provider):
        analyzed = client.post(f"/api/v1/roles/{role_id}/analyze", json={})
    assert analyzed.status_code == 200, analyzed.text
    return role.json()