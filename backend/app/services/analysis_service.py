"""Analysis service: orchestrates the AI analysis pipeline.

Pipeline:  load role  →  gather context  →  build request  →  call provider
           →  validate output  →  normalise scores  →  persist RoleAnalysis
           →  persist AnalysisRun  →  return result
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from beanie import PydanticObjectId

from app.core.config import Settings
from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.models.analysis_run import AnalysisRun
from app.models.enums import AnalysisRunStatus, ImpactLevel, ReskillingPriority
from app.models.role_analysis import (
    ActivityImpact,
    AiExposureSummary,
    FutureResponsibility,
    FutureSkill,
    ModelMetadata,
    Recommendation,
    RoleAnalysis,
    SkillGap,
)
from app.repositories.analysis_run import AnalysisRunRepository
from app.repositories.role_analysis import RoleAnalysisRepository
from app.schemas.analysis import CurrentSkillRead, RoleAnalysisRead
from app.services.ai import get_provider
from app.services.ai.base import (
    AIAnalysisRequest,
    AIAnalysisResult,
    AIProviderError,
    ActivityContext,
    ProcessContext,
    SkillContext,
)
from app.services.ai.prompt import ANALYSIS_VERSION, PROMPT_VERSION
from app.services.activity_service import ActivityService
from app.services.process_service import ProcessService
from app.services.role_service import RoleService
from app.services.skill_service import SkillService

logger = get_logger("services.analysis")

# ---------------------------------------------------------------------------
# Deterministic score helpers
# ---------------------------------------------------------------------------

_IMPACT_THRESHOLDS: list[tuple[float, ImpactLevel]] = [
    (0.7, ImpactLevel.HIGH),
    (0.4, ImpactLevel.MEDIUM),
    (0.2, ImpactLevel.LOW),
]

_RESKILLING_MAP: dict[str, ReskillingPriority] = {
    "low": ReskillingPriority.LOW,
    "medium": ReskillingPriority.MEDIUM,
    "high": ReskillingPriority.HIGH,
    "critical": ReskillingPriority.CRITICAL,
}


def _clamp(score: float) -> float:
    return max(0.0, min(1.0, score))


def _score_to_impact(score: float) -> ImpactLevel:
    for threshold, level in _IMPACT_THRESHOLDS:
        if score >= threshold:
            return level
    return ImpactLevel.NONE


def _parse_reskilling_priority(value: str) -> ReskillingPriority:
    normalised = value.strip().lower()
    return _RESKILLING_MAP.get(normalised, ReskillingPriority.MEDIUM)


def _compute_input_hash(request: AIAnalysisRequest) -> str:
    """Deterministic SHA-256 of the structured context for deduplication."""
    parts: list[str] = [
        request.role_id,
        request.role_name,
        request.role_description or "",
        request.industry or "",
        PROMPT_VERSION,
    ]
    for p in sorted(request.processes, key=lambda x: x.name):
        parts.extend([p.name, p.description or ""])
    for a in sorted(request.activities, key=lambda x: x.name):
        parts.extend([a.name, a.description or "", a.current_human_involvement])
    for s in sorted(request.current_skills, key=lambda x: x.name):
        parts.extend([s.name, s.category or "", s.description or ""])
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


# ---------------------------------------------------------------------------
# Context gathering
# ---------------------------------------------------------------------------

async def _build_request(
    role_id: PydanticObjectId, organization_id: PydanticObjectId
) -> AIAnalysisRequest:
    """Load all related data and assemble the analysis request.

    Context is role- AND organization-scoped: processes are those that own
    the role's activities, current skills are the ones linked to the role,
    and every referenced document must belong to the role's organization.
    This keeps the AI input truthful and prevents foreign-tenant data from
    leaking into another organization's analysis request.
    """
    role_service = RoleService()
    process_service = ProcessService()
    activity_service = ActivityService()
    skill_service = SkillService()

    role = await role_service.get(role_id, organization_id)

    activities, _ = await activity_service.list(
        organization_id=organization_id, role_id=role_id, limit=200
    )

    process_ids = sorted(
        {a.process_id for a in activities if a.process_id is not None}, key=str
    )
    processes: list = []
    for process_id in process_ids:
        process = await process_service.repository.get_by_id(process_id)
        if process is not None and process.organization_id == organization_id:
            processes.append(process)

    skills: list = []
    for skill_id in role.current_skill_ids or []:
        skill = await skill_service.repository.get_by_id(skill_id)
        if skill is not None:
            skills.append(skill)

    process_ctx = [
        ProcessContext(name=p.name, description=p.description)
        for p in processes
    ]
    activity_ctx = [
        ActivityContext(
            temp_ref=f"act_{i}",
            name=a.name,
            description=a.description,
            current_human_involvement=a.current_human_involvement,
        )
        for i, a in enumerate(activities)
    ]
    skill_ctx = [
        SkillContext(name=s.name, category=s.category, description=s.description)
        for s in skills
    ]

    return AIAnalysisRequest(
        role_id=str(role.id),
        role_name=role.name,
        role_description=role.description,
        industry=role.industry,
        processes=process_ctx,
        activities=activity_ctx,
        current_skills=skill_ctx,
    )


def _validate_context(request: AIAnalysisRequest) -> None:
    """Reject empty/meaningless contexts before any AI call.

    An analysis of a role with no industry, no activities, or no current
    skills would otherwise let the provider fabricate a convincing-looking
    result from nothing. Such requests are refused with a clear error.
    """
    problems: list[str] = []
    if not (request.industry or "").strip():
        problems.append("Industry is required to provide analysis context")
    if not request.activities:
        problems.append("At least one activity is required for analysis")
    if not request.current_skills:
        problems.append("At least one current skill is required for analysis")
    if problems:
        raise ValidationError("; ".join(problems))


# ---------------------------------------------------------------------------
# Result normalisation
# ---------------------------------------------------------------------------

async def _normalise_and_persist(
    result: AIAnalysisResult,
    request: AIAnalysisRequest,
    provider_name: str,
    model_name: str,
    organization_id: PydanticObjectId,
) -> RoleAnalysis:
    """Map temp refs → ObjectIds, normalise scores, persist, and return."""

    # Build temp_ref → real ObjectId mapping
    activity_map: dict[str, PydanticObjectId] = {}
    if request.activities:
        activity_service = ActivityService()
        all_activities, _ = await activity_service.list(
            organization_id=organization_id,
            role_id=PydanticObjectId(request.role_id),
            limit=200,
        )
        for i, act in enumerate(all_activities):
            if act.id is not None:
                activity_map[f"act_{i}"] = act.id

    # Build activity impacts with real IDs
    activity_impacts = []
    for impact in result.activity_impacts:
        real_id = activity_map.get(impact.activity_ref)
        if real_id is None:
            logger.warning("Unknown activity_ref %s, skipping", impact.activity_ref)
            continue
        activity_impacts.append(
            ActivityImpact(
                activity_id=real_id,
                activity_name=impact.activity_ref,
                impact_level=_score_to_impact(impact.automation_score),
                automation_score=_clamp(impact.automation_score),
                augmentation_score=_clamp(impact.augmentation_score),
                human_responsibility=impact.human_responsibility,
                description=impact.description,
            )
        )

    # Build nested structures
    future_responsibilities = [
        FutureResponsibility(
            title=fr.title,
            description=fr.description,
            rationale=fr.rationale,
        )
        for fr in result.future_responsibilities
    ]
    future_skills = [
        FutureSkill(
            name=fs.name,
            category=fs.category,
            relevance=_clamp(fs.relevance),
            priority=_parse_reskilling_priority(fs.priority),
        )
        for fs in result.future_skills
    ]
    recommendations = [
        Recommendation(
            title=r.title,
            description=r.description,
            rationale=r.rationale,
            priority=_parse_reskilling_priority(r.priority),
        )
        for r in result.recommendations
    ]

    # Compute skill gaps: a future skill is a gap only when it is not
    # covered (by name) in the role's current skills.
    current_skill_names = {
        s.name.strip().lower() for s in request.current_skills if s.name
    }
    skill_gaps = [
        SkillGap(
            skill_name=fs.name,
            category=fs.category,
            relevance=_clamp(fs.relevance),
            priority=_parse_reskilling_priority(fs.priority),
            reason=(
                "Required in the future role but absent from the role's "
                "current skills"
            ),
        )
        for fs in result.future_skills
        if fs.name.strip().lower() not in current_skill_names
    ]

    # Resolve human-friendly activity names from the request
    ref_to_name = {a.temp_ref: a.name for a in request.activities}
    for imp in activity_impacts:
        friendly = ref_to_name.get(imp.activity_name)
        if friendly:
            imp.activity_name = friendly

    # Persist RoleAnalysis
    analysis = RoleAnalysis(
        organization_id=organization_id,
        role_id=PydanticObjectId(request.role_id),
        analysis_version=ANALYSIS_VERSION,
        ai_exposure=AiExposureSummary(
            score=_clamp(result.ai_exposure_score),
            level=_score_to_impact(result.ai_exposure_score),
            summary=result.ai_exposure_summary,
        ),
        automation_score=_clamp(result.automation_score),
        augmentation_score=_clamp(result.augmentation_score),
        reskilling_priority=_parse_reskilling_priority(result.reskilling_priority),
        activity_impacts=activity_impacts,
        future_responsibilities=future_responsibilities,
        future_skills=future_skills,
        skill_gaps=skill_gaps,
        recommendations=recommendations,
        reasoning=result.reasoning,
        model_metadata=ModelMetadata(
            provider=provider_name,
            model=model_name,
            model_version=None,
            prompt_version=PROMPT_VERSION,
        ),
    )
    repo = RoleAnalysisRepository()
    return await repo.create(analysis)


# ---------------------------------------------------------------------------
# Public service
# ---------------------------------------------------------------------------

class AnalysisService:
    def __init__(self) -> None:
        self._analysis_repo = RoleAnalysisRepository()
        self._run_repo = AnalysisRunRepository()
        self._role_service = RoleService()

    async def get_latest_for_role(
        self, role_id: PydanticObjectId, organization_id: PydanticObjectId
    ) -> RoleAnalysis | None:
        """Return the newest persisted analysis for a role, if any.

        The role lookup is organization-scoped: a role from another
        organization is indistinguishable from a missing one (404).
        """
        await self._role_service.get(role_id, organization_id)
        return await self._analysis_repo.latest_for_role(role_id, organization_id)

    async def to_read(self, analysis: RoleAnalysis) -> RoleAnalysisRead:
        """Build a RoleAnalysisRead enriched with the role's current skills.

        ``current_skills`` are role data resolved at read time (the analysis
        document stores future skills and gaps, not the current skill set).
        The role is resolved within the analysis's own organization.
        """
        data = RoleAnalysisRead.model_validate(analysis).model_dump()
        current_skills: list[CurrentSkillRead] = []
        try:
            role = await self._role_service.get(
                analysis.role_id, analysis.organization_id
            )
        except NotFoundError:
            role = None
        if role is not None and role.current_skill_ids:
            skill_service = SkillService()
            for skill_id in role.current_skill_ids:
                skill = await skill_service.repository.get_by_id(skill_id)
                if skill is not None:
                    current_skills.append(
                        CurrentSkillRead(name=skill.name, category=skill.category)
                    )
        data["current_skills"] = current_skills
        return RoleAnalysisRead(**data)

    async def analyze_role(
        self,
        role_id: PydanticObjectId,
        *,
        settings: Settings,
        force: bool = False,
        organization_id: PydanticObjectId,
    ) -> RoleAnalysis:
        """Run the full analysis pipeline for a role within an organization.

        1.  Load role and related context (organization-scoped; a foreign
            role is a 404 and the provider is never invoked).
        2.  Call the configured AI provider.
        3.  Validate and normalise the structured output.
        4.  Persist RoleAnalysis and AnalysisRun records.
        5.  Return the persisted analysis.

        Deduplication: if a completed AnalysisRun with the same input hash
        exists WITHIN THE SAME ORGANIZATION, the existing RoleAnalysis is
        returned unless ``force=True``. One tenant can never receive another
        tenant's cached analysis.
        """
        provider = get_provider(settings)

        # 0. Tenant boundary: resolve the role inside the caller's org.
        #    A foreign/missing role raises 404 BEFORE any provider call.
        await self._role_service.get(role_id, organization_id)

        # 1. Build structured request
        request = await _build_request(role_id, organization_id)

        # 1b. Data-quality gate: refuse empty/meaningless contexts.
        _validate_context(request)

        input_hash = _compute_input_hash(request)

        # 2. Dedup check (organization-scoped)
        if not force:
            existing_run = await self._run_repo.find_completed_by_input_hash(
                input_hash, organization_id
            )
            if existing_run and existing_run.role_analysis_id:
                existing = await self._analysis_repo.get_by_id(
                    existing_run.role_analysis_id
                )
                if existing:
                    logger.info(
                        "Returning cached analysis for role %s (hash=%s)",
                        role_id,
                        input_hash[:12],
                    )
                    return existing

        # 3. Create AnalysisRun (audit trail)
        run = AnalysisRun(
            organization_id=organization_id,
            role_id=role_id,
            provider=provider.name,
            model=settings.ai_model,
            prompt_version=PROMPT_VERSION,
            input_hash=input_hash,
            status=AnalysisRunStatus.RUNNING,
            started_at=datetime.now(UTC),
        )
        run = await self._run_repo.create(run)

        # 4. Call provider
        try:
            raw_result = await provider.analyze_role(request)
        except AIProviderError:
            run.status = AnalysisRunStatus.FAILED
            run.completed_at = datetime.now(UTC)
            run.error = "Provider error (see application logs)"
            await self._run_repo.update(run)
            raise
        except Exception as exc:
            run.status = AnalysisRunStatus.FAILED
            run.completed_at = datetime.now(UTC)
            run.error = f"Unexpected provider error: {type(exc).__name__}"
            await self._run_repo.update(run)
            raise

        # 5. Validate provider output against schema
        if isinstance(raw_result, AIAnalysisResult):
            result = raw_result
        else:
            try:
                result = AIAnalysisResult.model_validate(raw_result)
            except Exception as exc:
                run.status = AnalysisRunStatus.FAILED
                run.completed_at = datetime.now(UTC)
                run.error = "AI output failed validation"
                await self._run_repo.update(run)
                from app.services.ai.base import AIOutputValidationError
                raise AIOutputValidationError(
                    f"AI output schema validation failed: {exc}"
                ) from exc

        # 6. Normalise, persist RoleAnalysis
        analysis = await _normalise_and_persist(
            result,
            request,
            provider_name=provider.name,
            model_name=settings.ai_model,
            organization_id=organization_id,
        )

        # 7. Update AnalysisRun
        run.status = AnalysisRunStatus.COMPLETED
        run.completed_at = datetime.now(UTC)
        run.role_analysis_id = analysis.id
        await self._run_repo.update(run)

        logger.info(
            "Analysis completed for role %s: analysis_id=%s run_id=%s",
            role_id,
            analysis.id,
            run.id,
        )
        return analysis
