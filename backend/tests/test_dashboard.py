"""Tests for Phase 3 endpoints: dashboard summary, skills summary, compare, analyze-new.

These exercise the real pipeline (with a mocked AI provider) so aggregation
logic is verified against persisted RoleAnalysis data.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

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

HIGH_RESULT = AIAnalysisResult(
    ai_exposure_score=0.82,
    ai_exposure_summary="High exposure: routine activities are automatable.",
    automation_score=0.75,
    augmentation_score=0.65,
    reskilling_priority="high",
    activity_impacts=[
        ActivityImpactOutput(
            activity_ref="act_0",
            automation_score=0.9,
            augmentation_score=0.2,
            description="Data entry is highly automatable.",
        )
    ],
    future_responsibilities=[
        FutureResponsibilityOutput(
            title="AI Oversight",
            description="Supervise AI outputs.",
            rationale="Automation shifts focus to validation.",
        )
    ],
    future_skills=[
        FutureSkillOutput(
            name="AI Prompt Engineering",
            category="Technical",
            relevance=0.9,
            priority="high",
        ),
        FutureSkillOutput(
            name="Data Storytelling",
            category="Analytical",
            relevance=0.6,
            priority="medium",
        ),
    ],
    recommendations=[
        RecommendationOutput(
            title="Invest in AI Literacy",
            description="Train on working with AI tools.",
            rationale="High augmentation potential.",
            priority="high",
        )
    ],
    reasoning="Routine tasks drive high automation; supervision emerges.",
)

LOW_RESULT = AIAnalysisResult(
    ai_exposure_score=0.2,
    ai_exposure_summary="Low exposure: role relies on human judgment.",
    automation_score=0.15,
    augmentation_score=0.3,
    reskilling_priority="low",
    future_skills=[
        FutureSkillOutput(
            name="AI Prompt Engineering",
            category="Technical",
            relevance=0.4,
            priority="medium",
        )
    ],
    reasoning="Limited automation potential.",
)


def _mock_provider(result: AIAnalysisResult):
    mock_provider = AsyncMock()
    mock_provider.name = "deepseek"
    mock_provider.analyze_role.return_value = result
    return mock_provider


def _analyze(
    client: TestClient, role_id: str, result: AIAnalysisResult, force: bool = False
) -> dict:
    with patch(
        "app.services.analysis_service.get_provider",
        return_value=_mock_provider(result),
    ):
        resp = client.post(
            f"/api/v1/roles/{role_id}/analyze", json={"force": force}
        )
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_dashboard_summary_empty(client: TestClient) -> None:
    resp = client.get("/api/v1/dashboard/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_roles"] == 0
    assert body["roles_analyzed"] == 0
    assert body["high_ai_impact_roles"] == 0
    assert body["high_automation_activities"] == 0
    assert body["high_reskilling_priority_roles"] == 0
    assert body["top_future_skills"] == []
    assert body["recent_role_analyses"] == []
    distribution = {item["level"]: item["count"] for item in body["ai_impact_distribution"]}
    assert distribution == {"none": 0, "low": 0, "medium": 0, "high": 0}


def test_dashboard_summary_reflects_analysis(client: TestClient) -> None:
    org = create_organization(client, "Finance Corp")
    analyzed = create_role_with_context(
        client,
        org["id"],
        name="Data Analyst",
        activities=[("Reporting", "Data Entry")],
        skills=["Data Analysis"],
    )
    create_role(client, org["id"], name="Chief of Staff")

    _analyze(client, analyzed["id"], HIGH_RESULT)

    resp = client.get("/api/v1/dashboard/summary")
    assert resp.status_code == 200
    body = resp.json()

    assert body["total_roles"] == 2
    assert body["roles_analyzed"] == 1
    assert body["high_ai_impact_roles"] == 1
    assert body["high_automation_activities"] == 1
    assert body["high_reskilling_priority_roles"] == 1

    distribution = {item["level"]: item["count"] for item in body["ai_impact_distribution"]}
    assert distribution == {"none": 0, "low": 0, "medium": 0, "high": 1}

    assert len(body["top_future_skills"]) == 2
    top = body["top_future_skills"][0]
    assert top["name"] == "AI Prompt Engineering"
    assert top["roles"] == 1
    assert top["priority"] == "high"

    assert len(body["recent_role_analyses"]) == 1
    recent = body["recent_role_analyses"][0]
    assert recent["role_name"] == "Data Analyst"
    assert recent["ai_exposure_score"] == 0.82
    assert recent["reskilling_priority"] == "high"
    assert recent["activity_count"] == 1


def test_dashboard_summary_latest_per_role(client: TestClient) -> None:
    org = create_organization(client, "Org")
    role = create_role_with_context(client, org["id"], name="Analyst")

    _analyze(client, role["id"], HIGH_RESULT)
    _analyze(client, role["id"], LOW_RESULT, force=True)

    resp = client.get("/api/v1/dashboard/summary")
    body = resp.json()
    assert body["roles_analyzed"] == 1
    assert body["high_ai_impact_roles"] == 0
    assert body["high_reskilling_priority_roles"] == 0


def test_skills_summary_aggregates_demand(client: TestClient) -> None:
    org = create_organization(client, "Org")
    role_a = create_role_with_context(client, org["id"], name="Role A")
    role_b = create_role_with_context(client, org["id"], name="Role B")

    _analyze(client, role_a["id"], HIGH_RESULT)
    _analyze(client, role_b["id"], LOW_RESULT)

    resp = client.get("/api/v1/dashboard/skills")
    assert resp.status_code == 200
    body = resp.json()
    by_name = {item["name"]: item for item in body["items"]}
    prompt = by_name["AI Prompt Engineering"]
    assert len(prompt["roles"]) == 2
    names = {ref["role_name"] for ref in prompt["roles"]}
    assert names == {"Role A", "Role B"}
    data_story = by_name["Data Storytelling"]
    assert len(data_story["roles"]) == 1
    assert data_story["roles"][0]["role_name"] == "Role A"


def test_compare_roles(client: TestClient) -> None:
    org = create_organization(client, "Org")
    analyzed = create_role_with_context(client, org["id"], name="Analyzed Role")
    unanalyzed = create_role(client, org["id"], name="Unanalyzed Role")

    _analyze(client, analyzed["id"], HIGH_RESULT)

    resp = client.get(
        f"/api/v1/roles/compare?role_ids={analyzed['id']}&role_ids={unanalyzed['id']}"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["roles"]) == 2
    by_id = {item["role"]["id"]: item for item in body["roles"]}
    assert by_id[analyzed["id"]]["has_analysis"] is True
    assert by_id[analyzed["id"]]["analysis"]["ai_exposure"]["score"] == 0.82
    assert by_id[unanalyzed["id"]]["has_analysis"] is False
    assert by_id[unanalyzed["id"]]["analysis"] is None


def test_compare_roles_missing_role_404(client: TestClient) -> None:
    resp = client.get(
        "/api/v1/roles/compare?role_ids=507f1f77bcf86cd799439011"
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "role_not_found"


def test_analyze_new_role_creates_and_analyzes(client: TestClient) -> None:
    with patch(
        "app.services.analysis_service.get_provider",
        return_value=_mock_provider(HIGH_RESULT),
    ):
        resp = client.post(
            "/api/v1/roles/analyze-new",
            json={
                "name": "Supply Chain Manager",
                "industry": "Manufacturing",
                "description": "Oversees supply chain operations.",
                "processes": [
                    {
                        "name": "Demand Planning",
                        "description": "Forecast and plan demand.",
                        "activities": ["Forecast Demand", "Analyze Historical Demand"],
                    }
                ],
                "current_skills": ["Supply Chain Management", "Forecasting"],
            },
        )
    assert resp.status_code == 201, resp.text
    body = resp.json()

    assert body["role"]["name"] == "Supply Chain Manager"
    assert body["role"]["industry"] == "Manufacturing"
    assert body["analysis"]["role_id"] == body["role"]["id"]
    assert body["analysis"]["ai_exposure"]["score"] == 0.82
    assert body["analysis"]["model_metadata"]["provider"] == "deepseek"

    persisted = client.get(f"/api/v1/roles/{body['role']['id']}")
    assert persisted.status_code == 200
    assert persisted.json()["name"] == "Supply Chain Manager"

    # The new role's processes, activities, and current skills are persisted.
    role_analysis = client.get(f"/api/v1/roles/{body['role']['id']}/analysis")
    assert role_analysis.status_code == 200
    latest = role_analysis.json()["latest"]
    assert {s["name"] for s in latest["current_skills"]} == {
        "Supply Chain Management",
        "Forecasting",
    }


def test_analyze_new_role_creates_default_org(client: TestClient) -> None:
    with patch(
        "app.services.analysis_service.get_provider",
        return_value=_mock_provider(LOW_RESULT),
    ):
        resp = client.post(
            "/api/v1/roles/analyze-new",
            json={
                "name": "Brand New Role",
                "industry": "Technology",
                "processes": [{"name": "Development", "activities": ["Code Reviews"]}],
                "current_skills": ["Programming"],
            },
        )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    orgs = client.get("/api/v1/organizations").json()
    assert any(org["name"] == "Default Organization" for org in orgs["items"])


def test_analyze_new_role_validation(client: TestClient) -> None:
    resp = client.post("/api/v1/roles/analyze-new", json={"name": ""})
    assert resp.status_code == 422


def test_analyze_new_role_requires_context(client: TestClient) -> None:
    """analyze-new without processes/skills is refused with 422."""
    resp = client.post(
        "/api/v1/roles/analyze-new",
        json={"name": "Empty Role", "industry": "Technology"},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "validation_error"


def test_list_roles_search_and_industry(client: TestClient) -> None:
    org = create_organization(client, "Org")
    role = create_role_with_context(client, org["id"], name="Supply Chain Analyst")
    create_role(client, org["id"], name="Finance Manager")

    _analyze(client, role["id"], HIGH_RESULT)

    resp = client.get("/api/v1/roles?search=supply")
    body = resp.json()
    assert body["meta"]["total"] == 1
    assert body["items"][0]["name"] == "Supply Chain Analyst"

    resp = client.get("/api/v1/roles?industry=Technology")
    body = resp.json()
    assert body["meta"]["total"] == 2

    enriched = body["items"][0]
    assert "has_analysis" in enriched
    assert "ai_exposure_level" in enriched
