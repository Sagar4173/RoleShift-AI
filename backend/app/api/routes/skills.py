"""Skill routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.schemas.common import Page, PageMeta, pagination_params
from app.schemas.skill import SkillCreate, SkillRead
from app.services.skill_service import SkillService

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("", response_model=Page[SkillRead])
async def list_skills(
    category: str | None = Query(default=None, max_length=100),
    pagination: tuple[int, int] = Depends(pagination_params),
    service: SkillService = Depends(),
) -> Page[SkillRead]:
    skip, limit = pagination
    items, total = await service.list(category=category, skip=skip, limit=limit)
    return Page[SkillRead](items=items, meta=PageMeta(skip=skip, limit=limit, total=total))


@router.post("", response_model=SkillRead, status_code=status.HTTP_201_CREATED)
async def create_skill(
    payload: SkillCreate,
    service: SkillService = Depends(),
) -> SkillRead:
    skill = await service.create(payload)
    return SkillRead.model_validate(skill)