"""Role service."""

from __future__ import annotations

import re

from beanie import PydanticObjectId

from app.core.exceptions import AppError, NotFoundError
from app.models.role import Role
from app.models.role_analysis import RoleAnalysis
from app.repositories.role import RoleRepository
from app.repositories.role_analysis import RoleAnalysisRepository
from app.schemas.activity import ActivityCreate
from app.schemas.process import ProcessCreate
from app.schemas.role import RoleCreate
from app.services.activity_service import ActivityService
from app.services.process_service import ProcessService
from app.services.skill_service import SkillService


def _build_filters(
    *,
    organization_id,
    industry: str | None,
    search: str | None,
) -> dict | None:
    filters: dict = {}
    if organization_id is not None:
        filters["organization_id"] = organization_id
    if industry:
        filters["industry"] = industry
    if search and search.strip():
        pattern = re.escape(search.strip())
        filters["$or"] = [
            {"name": {"$regex": pattern, "$options": "i"}},
            {"description": {"$regex": pattern, "$options": "i"}},
        ]
    return filters or None


class RoleService:
    def __init__(self) -> None:
        self.repository = RoleRepository()
        self._analysis_repo = RoleAnalysisRepository()

    async def create(self, payload: RoleCreate, organization_id: PydanticObjectId) -> Role:
        return await self.repository.create(
            Role(organization_id=organization_id, **payload.model_dump())
        )

    async def create_with_context(
        self,
        *,
        organization_id: PydanticObjectId,
        name: str,
        description: str | None,
        industry: str | None,
        processes: list,
        current_skills: list[str],
        allow_skill_catalogue_create: bool,
    ) -> Role:
        """Create a role together with its processes, activities, and skills.

        Processes and activities are created as real documents (activities are
        linked to the role), and ``current_skills`` are resolved against the
        global skill catalogue and linked onto the role. Missing catalogue
        names are only created when ``allow_skill_catalogue_create`` is true
        (OWNER/ADMIN flows); otherwise a missing name is a 422 and nothing is
        written. Any document whose id cannot be persisted is skipped, leaving
        a consistent, useful role.
        """
        role = await self.create(
            RoleCreate(
                name=name,
                description=description,
                industry=industry,
            ),
            organization_id=organization_id,
        )
        if role.id is None:
            raise AppError(
                "Failed to persist new role",
                code="internal_error",
                status_code=500,
            )

        sequence = 0
        process_service = ProcessService()
        activity_service = ActivityService()
        for process_input in processes:
            process = await process_service.create(
                ProcessCreate(
                    name=process_input.name,
                    description=process_input.description,
                    industry=industry,
                ),
                organization_id=organization_id,
            )
            if process.id is None:
                continue
            for activity_name in process_input.activities:
                await activity_service.create(
                    ActivityCreate(
                        process_id=process.id,
                        role_id=role.id,
                        name=activity_name,
                        sequence=sequence,
                    ),
                    organization_id=organization_id,
                )
                sequence += 1

        await self._replace_current_skills(
            role, current_skills, allow_skill_catalogue_create=allow_skill_catalogue_create
        )
        return role

    async def _replace_current_skills(
        self,
        role: Role,
        skill_names: list[str],
        *,
        allow_skill_catalogue_create: bool,
    ) -> None:
        """Resolve skill names against the catalogue and relink the role.

        Missing catalogue names are created only when the caller is
        explicitly authorized to extend the global catalogue (OWNER/ADMIN);
        otherwise a missing name raises a deterministic 422 and the role is
        left untouched (fail before any write — no partial mutation).
        """
        skill_service = SkillService()
        skill_ids: list[PydanticObjectId] = []
        for skill_name in skill_names:
            skill = await skill_service.get_or_create_by_name(
                skill_name, allow_create=allow_skill_catalogue_create
            )
            if skill.id is not None:
                skill_ids.append(skill.id)
        role.current_skill_ids = skill_ids
        await self.repository.update(role)

    async def set_current_skills(
        self,
        role_id,
        skill_names: list[str],
        organization_id: PydanticObjectId,
        *,
        allow_skill_catalogue_create: bool,
    ) -> Role:
        """Replace a role's current skills by name, then return the role.

        Catalogue creation semantics match ``_replace_current_skills``: only
        authorized callers (OWNER/ADMIN) may introduce missing names.
        """
        role = await self.get(role_id, organization_id)
        await self._replace_current_skills(
            role, skill_names, allow_skill_catalogue_create=allow_skill_catalogue_create
        )
        return role

    async def get(self, role_id, organization_id: PydanticObjectId) -> Role:
        role = await self.repository.get_by_id(role_id)
        if role is None or role.organization_id != organization_id:
            raise NotFoundError("Role not found", code="role_not_found")
        return role

    async def list(
        self, *, organization_id: PydanticObjectId, skip: int = 0, limit: int = 50
    ) -> tuple[list[Role], int]:
        filters = {"organization_id": organization_id}
        roles = await self.repository.list(skip=skip, limit=limit, filters=filters)
        total = await self.repository.count(filters)
        return roles, total

    async def list_with_analysis(
        self,
        *,
        organization_id: PydanticObjectId,
        industry: str | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[tuple[Role, RoleAnalysis | None]], int]:
        """List roles within an organization paired with their latest analysis."""
        filters = _build_filters(
            organization_id=organization_id,
            industry=industry,
            search=search,
        )
        roles = await self.repository.list(skip=skip, limit=limit, filters=filters)
        total = await self.repository.count(filters)
        role_ids = [role.id for role in roles if role.id is not None]
        analyses = await self._analysis_repo.latest_for_roles(role_ids, organization_id)
        return [
            (role, analyses.get(role.id) if role.id is not None else None)
            for role in roles
        ], total

    async def delete(self, role_id, organization_id: PydanticObjectId) -> None:
        role = await self.get(role_id, organization_id)
        await self.repository.delete(role)
