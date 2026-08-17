"""Session document for authentication.

Each session stores only the SHA-256 hash of an opaque random token; the
raw token travels exclusively inside the HttpOnly session cookie. Storing
hashes means a database read cannot recover usable session tokens.
"""

from __future__ import annotations

from datetime import datetime

from beanie import PydanticObjectId
from pydantic import Field
from pymongo import IndexModel

from app.models.common import BaseDocument


class Session(BaseDocument):
    user_id: PydanticObjectId
    token_hash: str = Field(min_length=64, max_length=64)
    expires_at: datetime

    class Settings:
        name = "sessions"
        indexes = [
            IndexModel("token_hash", unique=True),
            "user_id",
            "expires_at",
        ]