"""Analysis schemas for Phase 2: retrieval + analysis creation."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models.enums import ImpactLevel, ReskillingPriority
from app.schemas.common import ObjectIdStr
from app.schemas.role import RoleRead


class AnalyzeRequest(BaseModel):
    """Request body for POST .../roles/{role_id}/analyze."""

    model_config = ConfigDict(extra="forbid")

    force: bool = Field(
        default=False,
        description="If true, re-analyse even when a cached result exists for identical input",
    )


RoleName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]


class ProcessInput(BaseModel):
    """A process to create for a new role, with its activities."""

    model_config = ConfigDict(extra="forbid")

    name: RoleName
    description: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=2000)] = None
    activities: list[RoleName] = Field(default_factory=list, max_length=100)


class AnalyzeNewRequest(BaseModel):
    """Request body for POST .../roles/analyze-new: create + analyse a new role.

    ``processes`` and ``current_skills`` supply the role's real business
    context. They are required: an analysis of an empty role would silently
    fabricate a convincing-looking result, which Phase 4 forbids.
    """

    model_config = ConfigDict(extra="forbid")

    name: RoleName
    description: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=2000)] = None
    industry: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=100)] = None
    processes: list[ProcessInput] = Field(default_factory=list, max_length=50)
    current_skills: list[RoleName] = Field(default_factory=list, max_length=200)


class AnalyzeNewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: RoleRead
    analysis: RoleAnalysisRead


class RoleCompareItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: RoleRead
    has_analysis: bool
    analysis: RoleAnalysisRead | None = None


class RoleCompareResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    roles: list[RoleCompareItem]


class AiExposureSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    score: float
    level: ImpactLevel
    summary: str


class ActivityImpactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    activity_id: ObjectIdStr
    activity_name: str
    impact_level: ImpactLevel
    automation_score: float
    augmentation_score: float
    human_responsibility: str | None
    description: str | None


class FutureResponsibilityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    title: str
    description: str | None
    rationale: str | None


class FutureSkillRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    name: str
    category: str | None
    relevance: float
    priority: ReskillingPriority


class CurrentSkillRead(BaseModel):
    """A current skill of the role (resolved from the role's skill links)."""

    model_config = ConfigDict(extra="forbid")

    name: str
    category: str | None = None


class SkillGapRead(BaseModel):
    """A future skill the role does not currently cover."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    skill_name: str
    category: str | None
    relevance: float
    priority: ReskillingPriority
    reason: str


class RecommendationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    title: str
    description: str | None
    rationale: str | None
    priority: ReskillingPriority


class ModelMetadataRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    provider: str
    model: str | None
    model_version: str | None
    prompt_version: str | None


class RoleAnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: ObjectIdStr
    role_id: ObjectIdStr
    analysis_version: str
    ai_exposure: AiExposureSummaryRead
    automation_score: float
    augmentation_score: float
    reskilling_priority: ReskillingPriority
    activity_impacts: list[ActivityImpactRead]
    future_responsibilities: list[FutureResponsibilityRead]
    future_skills: list[FutureSkillRead]
    skill_gaps: list[SkillGapRead] = Field(default_factory=list)
    current_skills: list[CurrentSkillRead] = Field(
        default_factory=list,
        description="The role's current skills, resolved at read time (not part of the analysis document)",
    )
    recommendations: list[RecommendationRead]
    reasoning: str | None
    model_metadata: ModelMetadataRead | None
    created_at: datetime
    updated_at: datetime


class AnalysisStatusRead(BaseModel):
    """Response for GET .../analysis: present when an analysis exists.

    Phase 2 will add POST .../analyze to create these records.
    """

    model_config = ConfigDict(extra="forbid")

    role_id: ObjectIdStr
    has_analysis: bool = Field(default=False)
    latest: RoleAnalysisRead | None = None