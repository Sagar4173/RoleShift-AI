"""Dashboard / workforce-analytics schemas (Phase 3)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import ImpactLevel, ReskillingPriority
from app.schemas.common import ObjectIdStr


class ImpactDistributionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: ImpactLevel
    count: int


class FutureSkillAggregateItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    category: str | None
    relevance: float
    priority: ReskillingPriority
    roles: int


class RecentRoleAnalysisItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role_id: ObjectIdStr
    role_name: str
    industry: str | None
    ai_exposure_score: float
    ai_exposure_level: ImpactLevel
    automation_score: float
    augmentation_score: float
    reskilling_priority: ReskillingPriority
    analyzed_at: datetime
    activity_count: int
    future_skills_count: int


class DashboardSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_roles: int
    roles_analyzed: int
    high_ai_impact_roles: int
    high_automation_activities: int
    high_reskilling_priority_roles: int
    top_future_skills: list[FutureSkillAggregateItem]
    ai_impact_distribution: list[ImpactDistributionItem]
    recent_role_analyses: list[RecentRoleAnalysisItem]


class SkillRoleRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role_id: ObjectIdStr
    role_name: str


class SkillDemandItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    category: str | None
    relevance: float
    priority: ReskillingPriority
    roles: list[SkillRoleRef]


class SkillsSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[SkillDemandItem]
