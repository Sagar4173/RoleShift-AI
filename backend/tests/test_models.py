"""RoleAnalysis model validation tests (no HTTP calls, but Beanie must be
initialised so documents can be constructed).
"""

from __future__ import annotations

import pytest
from beanie import PydanticObjectId
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.models.enums import ImpactLevel, ReskillingPriority
from app.models.role_analysis import (
    ActivityImpact,
    AiExposureSummary,
    ModelMetadata,
    Recommendation,
    RoleAnalysis,
)


def _valid_role_analysis() -> RoleAnalysis:
    return RoleAnalysis(
        organization_id=PydanticObjectId("507f1f77bcf86cd799439010"),
        role_id=PydanticObjectId("507f1f77bcf86cd799439011"),
        ai_exposure=AiExposureSummary(score=0.6, level=ImpactLevel.HIGH, summary="Heavily exposed"),
        automation_score=0.5,
        augmentation_score=0.7,
        reskilling_priority=ReskillingPriority.HIGH,
        activity_impacts=[
            ActivityImpact(
                activity_id=PydanticObjectId("507f1f77bcf86cd799439012"),
                activity_name="Reporting",
                impact_level=ImpactLevel.HIGH,
                automation_score=0.9,
                augmentation_score=0.4,
            )
        ],
        recommendations=[Recommendation(title="Upskill in data tools", priority=ReskillingPriority.HIGH)],
        model_metadata=ModelMetadata(provider="placeholder", model="m"),
    )


def test_role_analysis_constructs_with_valid_data(client: TestClient) -> None:
    analysis = _valid_role_analysis()
    assert analysis.automation_score == 0.5
    assert analysis.activity_impacts[0].activity_name == "Reporting"


def test_role_analysis_rejects_out_of_range_scores(client: TestClient) -> None:
    with pytest.raises(ValidationError):
        RoleAnalysis(
            organization_id=PydanticObjectId("507f1f77bcf86cd799439010"),
            role_id=PydanticObjectId("507f1f77bcf86cd799439011"),
            ai_exposure=AiExposureSummary(score=0.5, summary="x"),
            automation_score=1.5,
            augmentation_score=0.5,
        )


def test_role_analysis_rejects_unknown_nested_fields(client: TestClient) -> None:
    with pytest.raises(ValidationError):
        RoleAnalysis(
            organization_id=PydanticObjectId("507f1f77bcf86cd799439010"),
            role_id=PydanticObjectId("507f1f77bcf86cd799439011"),
            ai_exposure=AiExposureSummary(score=0.5, summary="x", extra_thing="y"),
            automation_score=0.5,
            augmentation_score=0.5,
        )


def test_role_analysis_rejects_invalid_reskilling_priority(client: TestClient) -> None:
    with pytest.raises(ValidationError):
        RoleAnalysis(
            organization_id=PydanticObjectId("507f1f77bcf86cd799439010"),
            role_id=PydanticObjectId("507f1f77bcf86cd799439011"),
            ai_exposure=AiExposureSummary(score=0.5, summary="x"),
            automation_score=0.5,
            augmentation_score=0.5,
            reskilling_priority="extreme",
        )


def test_role_analysis_requires_organization_id(client: TestClient) -> None:
    """Phase 6.3: persisted analyses must always carry the tenant binding."""
    with pytest.raises(ValidationError):
        RoleAnalysis(  # type: ignore[call-arg]
            role_id=PydanticObjectId("507f1f77bcf86cd799439011"),
            ai_exposure=AiExposureSummary(score=0.5, summary="x"),
            automation_score=0.5,
            augmentation_score=0.5,
        )