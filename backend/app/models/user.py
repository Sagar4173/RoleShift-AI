"""User document for authentication.

Phase 6.2 scope: identity only. Organization membership and role-based
authorization are introduced in later phases (6.3 / 6.4) and deliberately
do not exist here.
"""

from __future__ import annotations

from pydantic import Field
from pymongo import IndexModel

from app.models.common import BaseDocument


class User(BaseDocument):
    email: str = Field(min_length=3, max_length=254)
    password_hash: str = Field(min_length=16, max_length=512)
    display_name: str = Field(min_length=1, max_length=120)
    is_active: bool = True

    class Settings:
        name = "users"
        indexes = [IndexModel("email", unique=True)]