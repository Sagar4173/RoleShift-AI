"""Organization membership document (Phase 6.4 RBAC).

Membership is the authorization relationship between a user and an
organization. The user identity document stays role-free; the role lives
here, keyed uniquely by (organization_id, user_id), so future
multi-organization membership is a schema-free evolution.

``User.organization_id`` remains the Phase 6.3 transitional "current
organization" pointer for session context; this document is the source of
truth for authorization.
"""

from __future__ import annotations

from beanie import PydanticObjectId
from pymongo import IndexModel

from app.models.common import BaseDocument
from app.models.enums import MemberRole


class OrganizationMembership(BaseDocument):
    organization_id: PydanticObjectId
    user_id: PydanticObjectId
    role: MemberRole

    class Settings:
        name = "organization_memberships"
        indexes = [
            IndexModel(
                [("organization_id", 1), ("user_id", 1)],
                unique=True,
            ),
            IndexModel("user_id"),
        ]