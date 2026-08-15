"""RoleAnalysis document: the persisted result of a role analysis run.

This is the structured, strongly-typed foundation the AI engine (Phase 2)
will populate. Scores are validated to the [0, 1] range; nested structures
reject unknown fields so stored analysis data stays clean and traceable.
"""

from __future__ import annotations

from beanie import PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field

from app.models.common import BaseDocument
from app.models.enums import ImpactLevel, ReskillingPriority


class AiExposureSummary(BaseModel):
    """Overall AI exposure for a role."""

    model_config = ConfigDict(extra="forbid")

    score: float = Field(ge=0.0, le=1.0)
    level: ImpactLevel = ImpactLevel.MEDIUM
    summary: str = Field(min_length=1, max_length=2000)


class ActivityImpact(BaseModel):
    """Per-activity automation/augmentation impact."""

    model_config = ConfigDict(extra="forbid")

    activity_id: PydanticObjectId
    activity_name: str = Field(min_length=1, max_length=150)
    impact_level: ImpactLevel = ImpactLevel.NONE
    automation_score: float = Field(default=0.0, ge=0.0, le=1.0)
    augmentation_score: float = Field(default=0.0, ge=0.0, le=1.0)
    human_responsibility: str | None = Field(default=None, max_length=2000)
    description: str | None = Field(default=None, max_length=2000)


class FutureResponsibility(BaseModel):
    """A new responsibility expected to emerge for the role."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    rationale: str | None = Field(default=None, max_length=2000)


class FutureSkill(BaseModel):
    """A skill the role will need in the future."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=150)
    category: str | None = Field(default=None, max_length=100)
    relevance: float = Field(default=0.0, ge=0.0, le=1.0)
    priority: ReskillingPriority = ReskillingPriority.LOW


class Recommendation(BaseModel):
    """An explainable recommendation produced by an analysis run."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    rationale: str | None = Field(default=None, max_length=2000)
    priority: ReskillingPriority = ReskillingPriority.LOW


class SkillGap(BaseModel):
    """A future skill required by the role that is absent or insufficient today.

    A gap exists only when a future skill is not covered (by name) in the
    role's current skill set. Computed deterministically in the analysis
    service from real current and future skills.
    """

    model_config = ConfigDict(extra="forbid")

    skill_name: str = Field(min_length=1, max_length=150)
    category: str | None = Field(default=None, max_length=100)
    relevance: float = Field(default=0.0, ge=0.0, le=1.0)
    priority: ReskillingPriority = ReskillingPriority.LOW
    reason: str = Field(min_length=1, max_length=2000)


class ModelMetadata(BaseModel):
    """Which provider/model/prompt produced this analysis (traceability)."""

    model_config = ConfigDict(extra="forbid")

    provider: str = Field(min_length=1, max_length=100)
    model: str | None = Field(default=None, max_length=200)
    model_version: str | None = Field(default=None, max_length=100)
    prompt_version: str | None = Field(default=None, max_length=100)


class RoleAnalysis(BaseDocument):
    role_id: PydanticObjectId
    analysis_version: str = Field(min_length=1, max_length=50, default="1.0")

    ai_exposure: AiExposureSummary
    automation_score: float = Field(ge=0.0, le=1.0)
    augmentation_score: float = Field(ge=0.0, le=1.0)
    reskilling_priority: ReskillingPriority = ReskillingPriority.LOW

    activity_impacts: list[ActivityImpact] = Field(default_factory=list)
    future_responsibilities: list[FutureResponsibility] = Field(default_factory=list)
    future_skills: list[FutureSkill] = Field(default_factory=list)
    skill_gaps: list[SkillGap] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)

    reasoning: str | None = Field(default=None, max_length=20000)
    model_metadata: ModelMetadata | None = None

    class Settings:
        name = "role_analyses"
        indexes = [[("role_id", 1), ("created_at", -1)], "role_id"]