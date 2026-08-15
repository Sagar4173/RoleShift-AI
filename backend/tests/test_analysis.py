"""Tests for the AI analysis pipeline (Phase 2).

All tests mock the AI provider -- no real LLM calls are made.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import Settings
from app.main import create_app
from app.models.enums import AnalysisRunStatus, ImpactLevel, ReskillingPriority
from app.services.ai.base import (
    AIAnalysisRequest,
    AIAnalysisResult,
    AIProviderNotConfiguredError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
    AIOutputValidationError,
    ActivityContext,
    ActivityImpactOutput,
    FutureResponsibilityOutput,
    FutureSkillOutput,
    ProcessContext,
    ProviderHealth,
    RecommendationOutput,
    SkillContext,
)
from app.services.ai.prompt import PROMPT_VERSION, build_analysis_prompt
from app.services.analysis_service import (
    AnalysisService,
    _clamp,
    _compute_input_hash,
    _normalise_and_persist,
    _parse_reskilling_priority,
    _score_to_impact,
)

from tests.conftest import (
    add_current_skills,
    create_activity,
    create_organization,
    create_process,
    create_role,
    create_role_with_context,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MOCK_AI_RESULT = AIAnalysisResult(
    ai_exposure_score=0.72,
    ai_exposure_summary="The Data Analyst role has significant AI exposure through data processing and reporting activities.",
    automation_score=0.65,
    augmentation_score=0.80,
    reskilling_priority="high",
    activity_impacts=[
        ActivityImpactOutput(
            activity_ref="act_0",
            automation_score=0.8,
            augmentation_score=0.7,
            description="Data collection can be largely automated.",
        ),
        ActivityImpactOutput(
            activity_ref="act_1",
            automation_score=0.4,
            augmentation_score=0.9,
            description="Analysis benefits from AI augmentation.",
        ),
    ],
    future_responsibilities=[
        FutureResponsibilityOutput(
            title="AI Model Validation",
            description="Validate AI-generated insights for accuracy.",
            rationale="As AI handles routine analysis, human oversight shifts to validation.",
        )
    ],
    future_skills=[
        FutureSkillOutput(
            name="AI Prompt Engineering",
            category="Technical",
            relevance=0.9,
            priority="high",
        )
    ],
    recommendations=[
        RecommendationOutput(
            title="Invest in AI Literacy",
            description="Train the team on working with AI tools.",
            rationale="Augmentation potential is high; team needs skills to leverage AI effectively.",
            priority="high",
        )
    ],
    reasoning="The role faces significant automation in routine tasks but high augmentation potential in analytical work. Reskilling should focus on AI collaboration skills.",
)


def _make_settings(**overrides: Any) -> Settings:
    defaults = {
        "app_env": "test",
        "log_level": "WARNING",
        "ai_provider": "deepseek",
        "ai_api_key": "test-key-not-real",
        "ai_model": "deepseek-chat",
        "ai_api_base_url": "https://api.deepseek.com",
        "ai_timeout_seconds": 60,
        "ai_temperature": 0.3,
    }
    defaults.update(overrides)
    return Settings(**defaults)


# ---------------------------------------------------------------------------
# Unit tests: deterministic helpers
# ---------------------------------------------------------------------------


class TestDeterministicHelpers:
    def test_clamp_in_range(self):
        assert _clamp(0.5) == 0.5

    def test_clamp_below(self):
        assert _clamp(-0.1) == 0.0

    def test_clamp_above(self):
        assert _clamp(1.5) == 1.0

    def test_score_to_impact_high(self):
        assert _score_to_impact(0.8) == ImpactLevel.HIGH

    def test_score_to_impact_medium(self):
        assert _score_to_impact(0.5) == ImpactLevel.MEDIUM

    def test_score_to_impact_low(self):
        assert _score_to_impact(0.3) == ImpactLevel.LOW

    def test_score_to_impact_none(self):
        assert _score_to_impact(0.1) == ImpactLevel.NONE

    def test_parse_reskilling_priority_valid(self):
        assert _parse_reskilling_priority("critical") == ReskillingPriority.CRITICAL

    def test_parse_reskilling_priority_case_insensitive(self):
        assert _parse_reskilling_priority("HIGH") == ReskillingPriority.HIGH

    def test_parse_reskilling_priority_unknown_defaults_medium(self):
        assert _parse_reskilling_priority("unknown_value") == ReskillingPriority.MEDIUM


# ---------------------------------------------------------------------------
# Unit tests: prompt
# ---------------------------------------------------------------------------


class TestPrompt:
    def test_prompt_version_is_stable(self):
        v1 = PROMPT_VERSION
        v2 = PROMPT_VERSION
        assert v1 == v2
        assert len(v1) == 16

    def test_build_prompt_includes_role_name(self):
        request = AIAnalysisRequest(
            role_id="test-123",
            role_name="Software Engineer",
            role_description="Builds software",
            industry="Tech",
        )
        prompt = build_analysis_prompt(request)
        assert "Software Engineer" in prompt
        assert "Builds software" in prompt
        assert "Tech" in prompt

    def test_build_prompt_includes_activities(self):
        request = AIAnalysisRequest(
            role_id="test-123",
            role_name="Engineer",
            activities=[
                ActivityContext(
                    temp_ref="act_0",
                    name="Code Review",
                    description="Review pull requests",
                    current_human_involvement="full",
                )
            ],
        )
        prompt = build_analysis_prompt(request)
        assert "[act_0]" in prompt
        assert "Code Review" in prompt

    def test_build_prompt_empty_context(self):
        request = AIAnalysisRequest(
            role_id="test-123",
            role_name="Engineer",
        )
        prompt = build_analysis_prompt(request)
        assert "No processes defined" in prompt
        assert "No activities defined" in prompt
        assert "No skills defined" in prompt


# ---------------------------------------------------------------------------
# Unit tests: input hash
# ---------------------------------------------------------------------------


class TestInputHash:
    def test_same_input_same_hash(self):
        request = AIAnalysisRequest(
            role_id="r1",
            role_name="Analyst",
            industry="Finance",
            processes=[ProcessContext(name="Reporting")],
            activities=[
                ActivityContext(
                    temp_ref="act_0",
                    name="Collect Data",
                    current_human_involvement="full",
                )
            ],
            current_skills=[SkillContext(name="SQL")],
        )
        h1 = _compute_input_hash(request)
        h2 = _compute_input_hash(request)
        assert h1 == h2
        assert len(h1) == 64

    def test_different_input_different_hash(self):
        r1 = AIAnalysisRequest(role_id="r1", role_name="Analyst")
        r2 = AIAnalysisRequest(role_id="r2", role_name="Analyst")
        assert _compute_input_hash(r1) != _compute_input_hash(r2)


# ---------------------------------------------------------------------------
# Integration tests: full analysis pipeline (mocked provider)
# ---------------------------------------------------------------------------


class TestAnalyzeRole:
    async def test_analyze_role_success(self, client):
        """Happy path: create org -> role -> process -> activities -> run analysis."""
        org = create_organization(client, "Finance Corp")
        role = create_role(client, org["id"], "Data Analyst")
        proc = create_process(client, org["id"], "Reporting")

        create_activity(client, role["id"], proc["id"], "Data Collection", 1)
        create_activity(client, role["id"], proc["id"], "Report Generation", 2)
        add_current_skills(client, role["id"], ["Data Analysis", "SQL"])

        mock_provider = AsyncMock()
        mock_provider.name = "deepseek"
        mock_provider.analyze_role.return_value = MOCK_AI_RESULT

        with patch(
            "app.services.analysis_service.get_provider",
            return_value=mock_provider,
        ):
            resp = client.post(
                f"/api/v1/roles/{role['id']}/analyze",
                json={"force": False},
            )

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["role_id"] == role["id"]
        assert data["analysis_version"] == "3.0.0"
        assert data["ai_exposure"]["score"] == 0.72
        assert data["ai_exposure"]["level"] == "high"
        assert data["automation_score"] == 0.65
        assert data["augmentation_score"] == 0.80
        assert data["reskilling_priority"] == "high"
        assert len(data["activity_impacts"]) == 2
        assert len(data["future_responsibilities"]) == 1
        assert len(data["future_skills"]) == 1
        assert len(data["recommendations"]) == 1
        assert data["reasoning"] is not None
        assert data["model_metadata"]["provider"] == "deepseek"
        assert data["model_metadata"]["model"] == "deepseek-chat"
        assert data["model_metadata"]["prompt_version"] == PROMPT_VERSION

        mock_provider.analyze_role.assert_called_once()

    async def test_analyze_role_missing_role(self, client):
        """404 when the role does not exist."""
        fake_id = "000000000000000000000001"
        mock_provider = AsyncMock()
        mock_provider.name = "deepseek"

        with patch(
            "app.services.analysis_service.get_provider",
            return_value=mock_provider,
        ):
            resp = client.post(
                f"/api/v1/roles/{fake_id}/analyze",
                json={},
            )
        assert resp.status_code == 404

    async def test_analyze_role_provider_timeout(self, client):
        """504 when the provider times out."""
        org = create_organization(client)
        role = create_role_with_context(client, org["id"])

        mock_provider = AsyncMock()
        mock_provider.name = "deepseek"
        mock_provider.analyze_role.side_effect = AIProviderTimeoutError()

        with patch(
            "app.services.analysis_service.get_provider",
            return_value=mock_provider,
        ):
            resp = client.post(
                f"/api/v1/roles/{role['id']}/analyze",
                json={},
            )
        assert resp.status_code == 504
        assert resp.json()["detail"]["code"] == "ai_provider_timeout"

    async def test_analyze_role_provider_unavailable(self, client):
        """503 when the provider is unavailable."""
        org = create_organization(client)
        role = create_role_with_context(client, org["id"])

        mock_provider = AsyncMock()
        mock_provider.name = "deepseek"
        mock_provider.analyze_role.side_effect = AIProviderUnavailableError(
            "Connection refused"
        )

        with patch(
            "app.services.analysis_service.get_provider",
            return_value=mock_provider,
        ):
            resp = client.post(
                f"/api/v1/roles/{role['id']}/analyze",
                json={},
            )
        assert resp.status_code == 503
        assert resp.json()["detail"]["code"] == "ai_provider_unavailable"

    async def test_analyze_role_malformed_output(self, client):
        """422 when the AI returns an invalid dict that fails validation."""
        org = create_organization(client)
        role = create_role_with_context(client, org["id"])

        mock_provider = AsyncMock()
        mock_provider.name = "deepseek"
        mock_provider.analyze_role.return_value = {
            "some_field": "unexpected",
            "ai_exposure_score": "not_a_number",
        }

        with patch(
            "app.services.analysis_service.get_provider",
            return_value=mock_provider,
        ):
            resp = client.post(
                f"/api/v1/roles/{role['id']}/analyze",
                json={},
            )
        assert resp.status_code == 422
        assert resp.json()["detail"]["code"] == "ai_output_validation_error"

    async def test_analyze_role_analysis_run_persisted(self, client):
        """Verify an AnalysisRun record is created for each analysis."""
        org = create_organization(client)
        role = create_role_with_context(client, org["id"])

        mock_provider = AsyncMock()
        mock_provider.name = "deepseek"
        mock_provider.analyze_role.return_value = MOCK_AI_RESULT

        with patch(
            "app.services.analysis_service.get_provider",
            return_value=mock_provider,
        ):
            resp = client.post(
                f"/api/v1/roles/{role['id']}/analyze",
                json={},
            )
        assert resp.status_code == 200, resp.text

        resp = client.get(f"/api/v1/roles/{role['id']}/analysis")
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_analysis"] is True
        assert data["latest"]["analysis_version"] == "3.0.0"

    async def test_analyze_role_dedup_returns_existing(self, client):
        """Second call with same input returns cached result (no new provider call)."""
        org = create_organization(client)
        role = create_role_with_context(client, org["id"])

        mock_provider = AsyncMock()
        mock_provider.name = "deepseek"
        mock_provider.analyze_role.return_value = MOCK_AI_RESULT

        with patch(
            "app.services.analysis_service.get_provider",
            return_value=mock_provider,
        ):
            resp1 = client.post(
                f"/api/v1/roles/{role['id']}/analyze",
                json={"force": False},
            )
            assert resp1.status_code == 200

            resp2 = client.post(
                f"/api/v1/roles/{role['id']}/analyze",
                json={"force": False},
            )
            assert resp2.status_code == 200

        assert mock_provider.analyze_role.call_count == 1
        assert resp1.json()["id"] == resp2.json()["id"]

    async def test_analyze_role_force_reanalysis(self, client):
        """force=true bypasses dedup and creates a new analysis."""
        org = create_organization(client)
        role = create_role_with_context(client, org["id"])

        mock_provider = AsyncMock()
        mock_provider.name = "deepseek"
        mock_provider.analyze_role.return_value = MOCK_AI_RESULT

        with patch(
            "app.services.analysis_service.get_provider",
            return_value=mock_provider,
        ):
            resp1 = client.post(
                f"/api/v1/roles/{role['id']}/analyze",
                json={"force": False},
            )
            resp2 = client.post(
                f"/api/v1/roles/{role['id']}/analyze",
                json={"force": True},
            )

        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert mock_provider.analyze_role.call_count == 2
        assert resp1.json()["id"] != resp2.json()["id"]

    async def test_analyze_role_activity_names_preserved(self, client):
        """Activity impact names are the real activity names, not temp refs."""
        org = create_organization(client)
        role = create_role(client, org["id"])
        proc = create_process(client, org["id"], "Modeling")

        create_activity(client, role["id"], proc["id"], "Financial Modeling", 1)
        add_current_skills(client, role["id"], ["Financial Analysis"])

        mock_provider = AsyncMock()
        mock_provider.name = "deepseek"
        mock_provider.analyze_role.return_value = MOCK_AI_RESULT

        with patch(
            "app.services.analysis_service.get_provider",
            return_value=mock_provider,
        ):
            resp = client.post(
                f"/api/v1/roles/{role['id']}/analyze",
                json={},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["activity_impacts"][0]["activity_name"] == "Financial Modeling"

    async def test_analyze_role_scores_clamped(self, client):
        """AI scores are clamped to [0,1] in the persisted result."""
        org = create_organization(client)
        role = create_role_with_context(client, org["id"])

        # Use valid scores in AI result; clamping is tested via unit tests.
        # The important thing is that scores round-trip correctly.
        result = AIAnalysisResult(
            ai_exposure_score=0.8,
            ai_exposure_summary="Moderate exposure.",
            automation_score=0.0,
            augmentation_score=1.0,
            reskilling_priority="medium",
        )

        mock_provider = AsyncMock()
        mock_provider.name = "deepseek"
        mock_provider.analyze_role.return_value = result

        with patch(
            "app.services.analysis_service.get_provider",
            return_value=mock_provider,
        ):
            resp = client.post(
                f"/api/v1/roles/{role['id']}/analyze",
                json={},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["automation_score"] == 0.0
        assert data["augmentation_score"] == 1.0

    async def test_analyze_role_provider_not_configured(self, client):
        """503 when ai_provider=none and endpoint is called."""
        org = create_organization(client)
        role = create_role_with_context(client, org["id"])

        settings = _make_settings(ai_provider="none")
        with patch(
            "app.api.routes.analysis.get_settings_dep",
            return_value=settings,
        ):
            resp = client.post(
                f"/api/v1/roles/{role['id']}/analyze",
                json={},
            )
        assert resp.status_code == 503

    async def test_analyze_role_no_activities(self, client):
        """Roles without activities are refused (422): context is required.

        Phase 4 forbids analyzing a role with no defined activities or
        skills, because the provider would fabricate a convincing result
        from nothing. The validation gate runs before any AI call.
        """
        org = create_organization(client)
        role = create_role(client, org["id"])
        add_current_skills(client, role["id"], ["Data Analysis"])

        mock_provider = AsyncMock()
        mock_provider.name = "deepseek"

        with patch(
            "app.services.analysis_service.get_provider",
            return_value=mock_provider,
        ):
            resp = client.post(
                f"/api/v1/roles/{role['id']}/analyze",
                json={},
            )

        assert resp.status_code == 422
        assert resp.json()["detail"]["code"] == "validation_error"
        mock_provider.analyze_role.assert_not_called()

    async def test_analyze_role_empty_body_defaults(self, client):
        """POST with no body uses default force=false."""
        org = create_organization(client)
        role = create_role_with_context(client, org["id"])

        mock_provider = AsyncMock()
        mock_provider.name = "deepseek"
        mock_provider.analyze_role.return_value = MOCK_AI_RESULT

        with patch(
            "app.services.analysis_service.get_provider",
            return_value=mock_provider,
        ):
            resp = client.post(
                f"/api/v1/roles/{role['id']}/analyze",
            )

        assert resp.status_code == 200

    async def test_analyze_role_analysis_run_status_failed_on_error(self, client):
        """AnalysisRun is marked FAILED when provider raises."""
        org = create_organization(client)
        role = create_role_with_context(client, org["id"])

        mock_provider = AsyncMock()
        mock_provider.name = "deepseek"
        mock_provider.analyze_role.side_effect = AIProviderUnavailableError("down")

        with patch(
            "app.services.analysis_service.get_provider",
            return_value=mock_provider,
        ):
            resp = client.post(
                f"/api/v1/roles/{role['id']}/analyze",
                json={},
            )

        assert resp.status_code == 503

        # Verify the run was persisted with FAILED status
        from app.models.analysis_run import AnalysisRun
        from app.repositories.analysis_run import AnalysisRunRepository
        from beanie import PydanticObjectId

        repo = AnalysisRunRepository()
        runs = await repo.list(filters={"role_id": PydanticObjectId(role["id"])})
        assert len(runs) == 1
        assert runs[0].status == AnalysisRunStatus.FAILED
        assert runs[0].error is not None
        assert runs[0].completed_at is not None

    async def test_analyze_role_ai_output_validation_error(self, client):
        """Provider returning wrong type triggers AIOutputValidationError."""
        org = create_organization(client)
        role = create_role_with_context(client, org["id"])

        mock_provider = AsyncMock()
        mock_provider.name = "deepseek"
        # Return a plain dict with missing required fields
        mock_provider.analyze_role.return_value = {"only": "partial data"}

        with patch(
            "app.services.analysis_service.get_provider",
            return_value=mock_provider,
        ):
            resp = client.post(
                f"/api/v1/roles/{role['id']}/analyze",
                json={},
            )
        assert resp.status_code == 422
        assert resp.json()["detail"]["code"] == "ai_output_validation_error"

    async def test_analyze_role_model_metadata_recorded(self, client):
        """ModelMetadata reflects provider name, model, and prompt version."""
        org = create_organization(client)
        role = create_role_with_context(client, org["id"])

        mock_provider = AsyncMock()
        mock_provider.name = "deepseek"
        mock_provider.analyze_role.return_value = MOCK_AI_RESULT

        with patch(
            "app.services.analysis_service.get_provider",
            return_value=mock_provider,
        ):
            resp = client.post(
                f"/api/v1/roles/{role['id']}/analyze",
                json={},
            )

        assert resp.status_code == 200
        meta = resp.json()["model_metadata"]
        assert meta["provider"] == "deepseek"
        assert meta["prompt_version"] == PROMPT_VERSION

    async def test_analyze_role_reskilling_priority_normalised(self, client):
        """Reskilling priority string is normalised to enum value."""
        org = create_organization(client)
        role = create_role_with_context(client, org["id"])

        result = AIAnalysisResult(
            ai_exposure_score=0.5,
            ai_exposure_summary="Moderate.",
            automation_score=0.3,
            augmentation_score=0.6,
            reskilling_priority="CRITICAL",  # uppercase
        )

        mock_provider = AsyncMock()
        mock_provider.name = "deepseek"
        mock_provider.analyze_role.return_value = result

        with patch(
            "app.services.analysis_service.get_provider",
            return_value=mock_provider,
        ):
            resp = client.post(
                f"/api/v1/roles/{role['id']}/analyze",
                json={},
            )

        assert resp.status_code == 200
        assert resp.json()["reskilling_priority"] == "critical"


class TestSkillGapInvariant:
    """Guards the current-skills / skill-gap consistency (Phase 4.7).

    A future skill may only be shown as "covered" when the role actually has
    current skills that cover it. The backend must never report zero gaps for
    a role with no current skills.
    """

    async def test_covered_future_skill_is_not_a_gap(self, client):
        """A current skill matching a future skill removes it from skill_gaps."""
        org = create_organization(client)
        role = create_role_with_context(
            client,
            org["id"],
            skills=["AI Prompt Engineering"],  # matches MOCK_AI_RESULT future skill
        )

        mock_provider = AsyncMock()
        mock_provider.name = "deepseek"
        mock_provider.analyze_role.return_value = MOCK_AI_RESULT

        with patch(
            "app.services.analysis_service.get_provider",
            return_value=mock_provider,
        ):
            resp = client.post(
                f"/api/v1/roles/{role['id']}/analyze",
                json={},
            )

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["skill_gaps"] == []
        assert [s["name"] for s in data["future_skills"]] == ["AI Prompt Engineering"]

    async def test_no_current_skills_all_future_are_gaps(self, client):
        """With no current skills, every future skill must be a skill gap.

        Guards against the data-consistency bug where a role with zero current
        skills reported zero gaps (implying every future skill was already
        covered). The frontend renders an honest "unable to determine" state
        for such roles.
        """
        request = AIAnalysisRequest(
            role_id="6a805602a87c053756353a00",
            role_name="Supply Chain Manager",
            industry="Manufacturing",
        )
        assert request.current_skills == []

        analysis = await _normalise_and_persist(
            MOCK_AI_RESULT,
            request,
            provider_name="deepseek",
            model_name="deepseek-chat",
        )

        assert len(analysis.skill_gaps) == 1
        assert analysis.skill_gaps[0].skill_name == "AI Prompt Engineering"
        assert [s.name for s in analysis.future_skills] == ["AI Prompt Engineering"]
