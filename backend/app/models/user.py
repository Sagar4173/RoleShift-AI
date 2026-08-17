"""User document for authentication.

Phase 6.2 scope: identity. Phase 6.3 adds ``organization_id`` as the
transitional single-organization binding (see the phase report for the
6.4 membership-based multi-organization transition path). Role-based
authorization is deliberately deferred to Phase 6.4 and does not exist
here.
"""

from __future__ import annotations

from beanie import PydanticObjectId
from pydantic import Field
from pymongo import IndexModel

from app.models.common import BaseDocument


class User(BaseDocument):
    email: str = Field(min_length=3, max_length=254)
    password_hash: str = Field(min_length=16, max_length=512)
    display_name: str = Field(min_length=1, max_length=120)
    organization_id: PydanticObjectId = Field(
        description="Phase 6.3 transitional organization binding (single organization per user)"
    )
    is_active: bool = True

    class Settings:
        name = "users"
        indexes = [
            IndexModel("email", unique=True),
            IndexModel("organization_id"),
        ]