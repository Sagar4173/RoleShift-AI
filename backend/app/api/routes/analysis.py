"""Role analysis routes.

Phase 2: POST /roles/{role_id}/analyze runs the AI analysis pipeline.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.deps import get_settings_dep
from app.core.config import Settings
from app.core.exceptions import AppError
from app.schemas.analysis import AnalysisStatusRead, AnalyzeRequest, RoleAnalysisRead
from app.schemas.common import ObjectIdStr
from app.services.analysis_service import AnalysisService
from app.services.ai.base import AIProviderError

router = APIRouter(prefix="/roles", tags=["analysis"])


@router.get("/{role_id}/analysis", response_model=AnalysisStatusRead)
async def get_role_analysis(
    role_id: ObjectIdStr,
    service: AnalysisService = Depends(),
) -> AnalysisStatusRead:
    """Return the latest persisted analysis for a role (if any)."""
    analysis = await service.get_latest_for_role(role_id)
    latest = await service.to_read(analysis) if analysis else None
    return AnalysisStatusRead(role_id=role_id, has_analysis=analysis is not None, latest=latest)


@router.post(
    "/{role_id}/analyze",
    response_model=RoleAnalysisRead,
    status_code=status.HTTP_200_OK,
)
async def analyze_role(
    role_id: ObjectIdStr,
    body: AnalyzeRequest | None = None,
    settings: Settings = Depends(get_settings_dep),
    service: AnalysisService = Depends(),
) -> RoleAnalysisRead:
    """Run the AI analysis pipeline for a role.

    Returns the persisted RoleAnalysis. Errors from the AI provider are
    mapped to appropriate HTTP status codes by the centralized handler.
    """
    force = body.force if body else False
    try:
        analysis = await service.analyze_role(
            role_id, settings=settings, force=force
        )
    except AIProviderError as exc:
        # Re-raise with provider-specific status code
        raise AppError(
            exc.message,
            code=exc.code,
            status_code=exc.status_code,
        ) from exc
    return await service.to_read(analysis)
