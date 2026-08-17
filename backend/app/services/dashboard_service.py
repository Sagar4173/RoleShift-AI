"""Dashboard service: workforce analytics aggregated from persisted data.

All metrics are computed from stored RoleAnalysis values (never fabricated),
reusing the impact thresholds already applied at persistence time.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from app.models.enums import ImpactLevel, ReskillingPriority
from app.models.role_analysis import RoleAnalysis
from app.repositories.role import RoleRepository
from app.repositories.role_analysis import RoleAnalysisRepository
from app.schemas.dashboard import (
    DashboardSummary,
    FutureSkillAggregateItem,
    ImpactDistributionItem,
    RecentRoleAnalysisItem,
    SkillDemandItem,
    SkillRoleRef,
    SkillsSummary,
)

_PRIORITY_RANK: dict[ReskillingPriority, int] = {
    ReskillingPriority.CRITICAL: 4,
    ReskillingPriority.HIGH: 3,
    ReskillingPriority.MEDIUM: 2,
    ReskillingPriority.LOW: 1,
}
_RANK_PRIORITY: dict[int, ReskillingPriority] = {
    rank: priority for priority, rank in _PRIORITY_RANK.items()
}
_RECENT_LIMIT = 8


class DashboardService:
    def __init__(self) -> None:
        self._role_repo = RoleRepository()
        self._analysis_repo = RoleAnalysisRepository()

    async def summary(self, organization_id) -> DashboardSummary:
        total_roles = await self._role_repo.count({"organization_id": organization_id})
        latest = await self._analysis_repo.all_grouped_latest(organization_id)

        high_ai_impact = sum(
            1 for a in latest.values() if a.ai_exposure.level == ImpactLevel.HIGH
        )
        high_automation_activities = sum(
            1
            for a in latest.values()
            for impact in a.activity_impacts
            if impact.impact_level == ImpactLevel.HIGH
        )
        high_reskilling = sum(
            1
            for a in latest.values()
            if a.reskilling_priority
            in (ReskillingPriority.HIGH, ReskillingPriority.CRITICAL)
        )

        distribution_counts = Counter(a.ai_exposure.level for a in latest.values())
        ai_impact_distribution = [
            ImpactDistributionItem(
                level=level, count=distribution_counts.get(level, 0)
            )
            for level in ImpactLevel
        ]

        top_future_skills = self._aggregate_future_skills(latest.values())[:10]

        recent = await self._analysis_repo.list_recent(organization_id, _RECENT_LIMIT)
        recent_role_analyses: list[RecentRoleAnalysisItem] = []
        for analysis in recent:
            role = await self._role_repo.get_by_id(analysis.role_id)
            if role is None:
                continue
            recent_role_analyses.append(
                RecentRoleAnalysisItem(
                    role_id=analysis.role_id,
                    role_name=role.name,
                    industry=role.industry,
                    ai_exposure_score=analysis.ai_exposure.score,
                    ai_exposure_level=analysis.ai_exposure.level,
                    automation_score=analysis.automation_score,
                    augmentation_score=analysis.augmentation_score,
                    reskilling_priority=analysis.reskilling_priority,
                    analyzed_at=analysis.created_at,
                    activity_count=len(analysis.activity_impacts),
                    future_skills_count=len(analysis.future_skills),
                )
            )

        return DashboardSummary(
            total_roles=total_roles,
            roles_analyzed=len(latest),
            high_ai_impact_roles=high_ai_impact,
            high_automation_activities=high_automation_activities,
            high_reskilling_priority_roles=high_reskilling,
            top_future_skills=top_future_skills,
            ai_impact_distribution=ai_impact_distribution,
            recent_role_analyses=recent_role_analyses,
        )

    async def skills_summary(self, organization_id) -> SkillsSummary:
        """Aggregate future-skill demand across the organization's analyzed roles."""
        latest = await self._analysis_repo.all_grouped_latest(organization_id)

        role_names: dict[object, str] = {}
        for analysis in latest.values():
            if analysis.role_id not in role_names:
                role = await self._role_repo.get_by_id(analysis.role_id)
                role_names[analysis.role_id] = role.name if role else "Unknown"

        aggregated: dict[str, dict] = {}
        for analysis in latest.values():
            for skill in analysis.future_skills:
                key = skill.name.strip().lower()
                entry = aggregated.setdefault(
                    key,
                    {
                        "name": skill.name,
                        "category": skill.category,
                        "relevance_sum": 0.0,
                        "priority_rank": 0,
                        "role_ids": set(),
                    },
                )
                entry["relevance_sum"] += skill.relevance
                entry["priority_rank"] = max(
                    entry["priority_rank"], _PRIORITY_RANK.get(skill.priority, 1)
                )
                entry["role_ids"].add(analysis.role_id)

        def _sort_key(entry: dict) -> tuple:
            return (
                -entry["priority_rank"],
                -entry["relevance_sum"] / len(entry["role_ids"]),
                entry["name"].lower(),
            )

        items: list[SkillDemandItem] = []
        for entry in sorted(aggregated.values(), key=_sort_key):
            role_count = len(entry["role_ids"])
            items.append(
                SkillDemandItem(
                    name=entry["name"],
                    category=entry["category"],
                    relevance=round(entry["relevance_sum"] / role_count, 4),
                    priority=_RANK_PRIORITY[entry["priority_rank"]],
                    roles=[
                        SkillRoleRef(
                            role_id=role_id,
                            role_name=role_names.get(role_id, "Unknown"),
                        )
                        for role_id in sorted(entry["role_ids"])
                    ],
                )
            )
        return SkillsSummary(items=items)

    @staticmethod
    def _aggregate_future_skills(
        analyses: Iterable[RoleAnalysis],
    ) -> list[FutureSkillAggregateItem]:
        aggregated: dict[str, dict] = {}
        for analysis in analyses:
            for skill in analysis.future_skills:
                key = skill.name.strip().lower()
                entry = aggregated.setdefault(
                    key,
                    {
                        "name": skill.name,
                        "category": skill.category,
                        "relevance_sum": 0.0,
                        "priority_rank": 0,
                        "count": 0,
                    },
                )
                entry["relevance_sum"] += skill.relevance
                entry["priority_rank"] = max(
                    entry["priority_rank"], _PRIORITY_RANK.get(skill.priority, 1)
                )
                entry["count"] += 1

        def _sort_key(entry: dict) -> tuple:
            return (
                -entry["count"],
                -entry["relevance_sum"] / entry["count"],
                entry["name"].lower(),
            )

        items: list[FutureSkillAggregateItem] = []
        for entry in sorted(aggregated.values(), key=_sort_key):
            count = entry["count"]
            items.append(
                FutureSkillAggregateItem(
                    name=entry["name"],
                    category=entry["category"],
                    relevance=round(entry["relevance_sum"] / count, 4),
                    priority=_RANK_PRIORITY[entry["priority_rank"]],
                    roles=count,
                )
            )
        return items
