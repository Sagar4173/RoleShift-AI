"""Phase 4 tests: full intelligence pipeline for arbitrary roles.

Covers role-scoped context gathering, activity-level impacts with human
responsibilities, skill-gap computation, persistence, deduplication, force
reanalysis, and validation gates. All tests are hermetic: the AI provider is
always mocked, never a real LLM call.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.models.enums import AnalysisRunStatus
from app.services.ai.base import (
    AIAnalysisResult,
    ActivityImpactOutput,
    FutureResponsibilityOutput,
    FutureSkillOutput,
    RecommendationOutput,
)

from tests.conftest import (
    add_current_skills,
    create_activity,
    create_organization,
    create_process,
    create_role,
    create_role_with_context,
)

FUTURE_SKILLS = [
    FutureSkillOutput(name="AI Model Validation", category="Technical", relevance=0.9, priority="high"),
    FutureSkillOutput(name="Data Storytelling", category="Analytical", relevance=0.6, priority="medium"),
]

RESULT = AIAnalysisResult(
    ai_exposure_score=0.78,
    ai_exposure_summary="High AI exposure across core activities.",
    automation_score=0.6,
    augmentation_score=0.7,
    reskilling_priority="high",
    activity_impacts=[
        ActivityImpactOutput(
            activity_ref="act_0",
            automation_score=0.8,
            augmentation_score=0.4,
            human_responsibility="Human approves final forecasts.",
            description="Automated forecasting.",
        ),
        ActivityImpactOutput(
            activity_ref="act_1",
            automation_score=0.3,
            augmentation_score=0.9,
            human_responsibility="Human validates supplier selections.",
            description="Augmented evaluation.",
        ),
        ActivityImpactOutput(
            activity_ref="act_2",
            automation_score=0.7,
            augmentation_score=0.5,
            human_responsibility="Human manages exceptions.",
            description="Semi-automated monitoring.",
        ),
        ActivityImpactOutput(
            activity_ref="act_3",
            automation_score=0.5,
            augmentation_score=0.6,
            human_responsibility="Human coordinates shipments.",
            description="Coordinated logistics.",
        ),
    ],
    future_responsibilities=[
        FutureResponsibilityOutput(
            title="AI Oversight",
            description="Supervise AI-driven decisions.",
            rationale="Automation shifts focus to oversight.",
        )
    ],
    future_skills=FUTURE_SKILLS,
    recommendations=[
        RecommendationOutput(
            title="Invest in AI Literacy",
            description="Train the team on AI tools.",
            rationale="High augmentation potential.",
            priority="high",
        )
    ],
    reasoning="Routine activities automate; humans shift to oversight and validation.",
)


def _mock_provider(result: AIAnalysisResult = RESULT) -> AsyncMock:
    mock_provider = AsyncMock()
    mock_provider.name = "deepseek"
    mock_provider.analyze_role.return_value = result
    return mock_provider


def _analyze_new(client: TestClient, payload: dict, result: AIAnalysisResult = RESULT) -> dict:
    with patch(
        "app.services.analysis_service.get_provider",
        return_value=_mock_provider(result),
    ):
        resp = client.post("/api/v1/roles/analyze-new", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


SUPPLY_CHAIN_PAYLOAD = {
    "name": "Supply Chain Manager",
    "industry": "Manufacturing",
    "description": "Oversees supply chain operations.",
    "processes": [
        {
            "name": "Demand Planning",
            "description": "Forecast and plan demand.",
            "activities": ["Forecast Demand", "Analyze Historical Demand"],
        },
        {
            "name": "Procurement",
            "description": "Source and select suppliers.",
            "activities": ["Evaluate Suppliers", "Compare Quotations"],
        },
    ],
    "current_skills": ["Supply Chain Management", "Demand Forecasting"],
}


# ---------------------------------------------------------------------------
# Full pipeline for a brand-new (arbitrary) role
# ---------------------------------------------------------------------------


def test_analyze_new_full_pipeline_persists_everything(client: TestClient) -> None:
    body = _analyze_new(client, SUPPLY_CHAIN_PAYLOAD)
    role_id = body["role"]["id"]

    assert body["role"]["name"] == "Supply Chain Manager"
    assert body["analysis"]["analysis_version"] == "3.0.0"

    # All 4 activities are mapped to real DB activities with real ids.
    impacts = body["analysis"]["activity_impacts"]
    assert len(impacts) == 4
    assert {imp["activity_name"] for imp in impacts} == {
        "Forecast Demand",
        "Analyze Historical Demand",
        "Evaluate Suppliers",
        "Compare Quotations",
    }
    assert all(imp["activity_id"] for imp in impacts)
    # The exposed ids are real ObjectIds, not "act_N" temp refs.
    assert all(imp["activity_id"] != "act_0" for imp in impacts)
    assert all("act_" not in imp["activity_id"] for imp in impacts)

    # Human responsibilities are populated per activity.
    assert all(imp["human_responsibility"] for imp in impacts)

    # Current skills resolve from the role's skill links.
    current_names = {s["name"] for s in body["analysis"]["current_skills"]}
    assert current_names == {"Supply Chain Management", "Demand Forecasting"}

    # Skill gaps: future skills not covered by current skills.
    gap_names = {g["skill_name"] for g in body["analysis"]["skill_gaps"]}
    assert gap_names == {"AI Model Validation", "Data Storytelling"}
    for gap in body["analysis"]["skill_gaps"]:
        assert gap["reason"]
        assert gap["priority"] in ("low", "medium", "high", "critical")

    # The role is persisted with processes + activities.
    processes = client.get("/api/v1/processes?organization_id=" + body["role"]["organization_id"])
    assert processes.status_code == 200
    process_names = {p["name"] for p in processes.json()["items"]}
    assert process_names == {"Demand Planning", "Procurement"}

    activities = client.get(f"/api/v1/activities?role_id={role_id}")
    assert activities.status_code == 200
    assert len(activities.json()["items"]) == 4


def test_analyze_new_arbitrary_roles(client: TestClient) -> None:
    """Finance Analyst and Marketing Manager both work end-to-end (no role-specific code)."""
    for payload in (
        {
            "name": "Finance Analyst",
            "industry": "Financial Services",
            "processes": [{"name": "Reporting", "activities": ["Close Books", "Produce Reports"]}],
            "current_skills": ["Accounting", "Excel"],
        },
        {
            "name": "Marketing Manager",
            "industry": "Consumer Goods",
            "processes": [{"name": "Campaigns", "activities": ["Plan Campaigns", "Measure ROI"]}],
            "current_skills": ["Marketing", "Analytics"],
        },
    ):
        body = _analyze_new(client, payload)
        assert body["role"]["name"] == payload["name"]
        assert len(body["analysis"]["activity_impacts"]) == 2


# ---------------------------------------------------------------------------
# Role-scoped context gathering
# ---------------------------------------------------------------------------


def test_request_is_role_scoped(client: TestClient) -> None:
    """Processes/skills sent to the provider come only from the role's own context."""
    org = create_organization(client, "Org")
    role_a = create_role_with_context(
        client,
        org["id"],
        name="Role A",
        activities=[("P1", "Activity A1")],
        skills=["Skill A"],
    )
    # An unrelated process owned by another role must NOT leak into A's request.
    role_b = create_role_with_context(
        client,
        org["id"],
        name="Role B",
        activities=[("P2", "Activity B1")],
        skills=["Skill B"],
    )
    assert role_b

    mock_provider = _mock_provider()
    with patch(
        "app.services.analysis_service.get_provider",
        return_value=mock_provider,
    ):
        resp = client.post(f"/api/v1/roles/{role_a['id']}/analyze", json={})
    assert resp.status_code == 200, resp.text

    request = mock_provider.analyze_role.call_args[0][0]
    assert [p.name for p in request.processes] == ["P1"]
    assert [a.name for a in request.activities] == ["Activity A1"]
    assert [s.name for s in request.current_skills] == ["Skill A"]


# ---------------------------------------------------------------------------
# Skill gaps
# ---------------------------------------------------------------------------


def test_skill_covered_is_not_a_gap(client: TestClient) -> None:
    """A future skill already in current skills is not reported as a gap."""
    body = _analyze_new(
        client,
        {
            "name": "Analyst",
            "industry": "Technology",
            "processes": [{"name": "Analysis", "activities": ["Run Reports"]}],
            "current_skills": ["AI Model Validation"],
        },
    )
    gaps = {g["skill_name"] for g in body["analysis"]["skill_gaps"]}
    assert gaps == {"Data Storytelling"}
    assert "AI Model Validation" not in gaps


def test_skill_gap_case_insensitive_match(client: TestClient) -> None:
    """Name matching for coverage is case-insensitive."""
    body = _analyze_new(
        client,
        {
            "name": "Analyst",
            "industry": "Technology",
            "processes": [{"name": "Analysis", "activities": ["Run Reports"]}],
            "current_skills": ["data storytelling"],
        },
    )
    gaps = {g["skill_name"] for g in body["analysis"]["skill_gaps"]}
    assert gaps == {"AI Model Validation"}


# ---------------------------------------------------------------------------
# Current-skills endpoint
# ---------------------------------------------------------------------------


def test_current_skills_endpoint_replaces_links(client: TestClient) -> None:
    org = create_organization(client, "Org")
    role = create_role(client, org["id"], name="Analyst")
    proc = create_process(client, org["id"], "Reporting")
    create_activity(client, role["id"], proc["id"], "Run Reports", 1)

    updated = add_current_skills(client, role["id"], ["SQL", "Python"])
    assert updated["id"] == role["id"]

    with patch(
        "app.services.analysis_service.get_provider",
        return_value=_mock_provider(),
    ):
        resp = client.post(f"/api/v1/roles/{role['id']}/analyze", json={})
    assert resp.status_code == 200, resp.text

    analysis = client.get(f"/api/v1/roles/{role['id']}/analysis").json()["latest"]
    assert {s["name"] for s in analysis["current_skills"]} == {"SQL", "Python"}


# ---------------------------------------------------------------------------
# Deduplication / force reanalysis
# ---------------------------------------------------------------------------


def test_analyze_new_creates_fresh_role_each_call(client: TestClient) -> None:
    """analyze-new always creates a brand-new role; nothing is accidentally cached."""
    provider = _mock_provider()
    with patch("app.services.analysis_service.get_provider", return_value=provider):
        first = client.post("/api/v1/roles/analyze-new", json=SUPPLY_CHAIN_PAYLOAD)
        assert first.status_code == 201
        second = client.post("/api/v1/roles/analyze-new", json=SUPPLY_CHAIN_PAYLOAD)
        assert second.status_code == 201

    assert provider.analyze_role.call_count == 2
    assert first.json()["role"]["id"] != second.json()["role"]["id"]
    assert first.json()["analysis"]["id"] != second.json()["analysis"]["id"]


def test_role_level_dedup_and_force(client: TestClient) -> None:
    """Re-analysing the same role with identical context is deduplicated; force bypasses."""
    org = create_organization(client, "Org")
    role = create_role_with_context(client, org["id"], name="Analyst")

    provider = _mock_provider()
    with patch("app.services.analysis_service.get_provider", return_value=provider):
        r1 = client.post(f"/api/v1/roles/{role['id']}/analyze", json={"force": False})
        r2 = client.post(f"/api/v1/roles/{role['id']}/analyze", json={"force": False})
        r3 = client.post(f"/api/v1/roles/{role['id']}/analyze", json={"force": True})

    assert r1.status_code == 200 and r2.status_code == 200 and r3.status_code == 200
    assert provider.analyze_role.call_count == 2
    assert r1.json()["id"] == r2.json()["id"]
    assert r3.json()["id"] != r1.json()["id"]


# ---------------------------------------------------------------------------
# Validation gates
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "No Industry", "processes": [{"name": "P", "activities": ["A"]}], "current_skills": ["S"]},
        {"name": "No Activities", "industry": "Tech", "current_skills": ["S"]},
        {"name": "No Skills", "industry": "Tech", "processes": [{"name": "P", "activities": ["A"]}]},
        {"name": "Empty Activities", "industry": "Tech", "processes": [{"name": "P", "activities": []}], "current_skills": ["S"]},
    ],
)
def test_analyze_new_context_gate(client: TestClient, payload: dict) -> None:
    with patch(
        "app.services.analysis_service.get_provider",
        return_value=_mock_provider(),
    ):
        resp = client.post("/api/v1/roles/analyze-new", json=payload)
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "validation_error"


def test_analyze_new_gate_runs_before_provider(client: TestClient) -> None:
    provider = _mock_provider()
    with patch("app.services.analysis_service.get_provider", return_value=provider):
        resp = client.post(
            "/api/v1/roles/analyze-new",
            json={"name": "Empty Role", "industry": "Tech"},
        )
    assert resp.status_code == 422
    provider.analyze_role.assert_not_called()


# ---------------------------------------------------------------------------
# Failure handling
# ---------------------------------------------------------------------------


async def test_analyze_failure_marks_run_failed(client: TestClient) -> None:
    org = create_organization(client, "Org")
    role = create_role_with_context(client, org["id"], name="Analyst")

    provider = _mock_provider()
    from app.services.ai.base import AIProviderUnavailableError

    provider.analyze_role.side_effect = AIProviderUnavailableError("down")
    with patch("app.services.analysis_service.get_provider", return_value=provider):
        resp = client.post(f"/api/v1/roles/{role['id']}/analyze", json={})
    assert resp.status_code == 503

    from beanie import PydanticObjectId
    from app.repositories.analysis_run import AnalysisRunRepository

    runs = await AnalysisRunRepository().list(
        filters={"role_id": PydanticObjectId(role["id"])}
    )
    assert len(runs) == 1
    assert runs[0].status == AnalysisRunStatus.FAILED


def test_analyze_malformed_output_is_rejected(client: TestClient) -> None:
    org = create_organization(client, "Org")
    role = create_role_with_context(client, org["id"], name="Analyst")

    provider = _mock_provider()
    provider.analyze_role.return_value = {"unexpected": "shape"}
    with patch("app.services.analysis_service.get_provider", return_value=provider):
        resp = client.post(f"/api/v1/roles/{role['id']}/analyze", json={})
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "ai_output_validation_error"


def test_activity_impacts_link_to_real_activities(client: TestClient) -> None:
    """Persisted impacts use the real activity ObjectIds created for the role."""
    body = _analyze_new(client, SUPPLY_CHAIN_PAYLOAD)
    role_id = body["role"]["id"]

    activities = client.get(f"/api/v1/activities?role_id={role_id}").json()["items"]
    db_ids = {a["id"] for a in activities}
    impact_ids = {imp["activity_id"] for imp in body["analysis"]["activity_impacts"]}
    assert impact_ids == db_ids
