"""Organization membership schemas (Phase 6.4 RBAC)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.models.enums import MemberRole


class MemberRoleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: MemberRole


class MemberRead(BaseModel):
    user_id: str
    email: str
    display_name: str
    role: str
    joined_at: str