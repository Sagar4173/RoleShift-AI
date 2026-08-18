"""MongoDB connection lifecycle (Motor client + Beanie ODM)."""

from __future__ import annotations

from collections.abc import AsyncIterator

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import Settings
from app.core.exceptions import DatabaseError
from app.core.logging import get_logger

logger = get_logger("core.database")

# Imported here so Beanie can discover every document class.
# The list is intentionally explicit: adding a new model means registering it
# here, which keeps startup behaviour predictable.
from app.models.activity import Activity
from app.models.analysis_run import AnalysisRun
from app.models.organization import Organization
from app.models.organization_membership import OrganizationMembership
from app.models.process import Process
from app.models.role import Role
from app.models.role_analysis import RoleAnalysis
from app.models.session import Session
from app.models.skill import Skill
from app.models.source import Source
from app.models.user import User

DOCUMENT_MODELS = [
    Organization,
    OrganizationMembership,
    Role,
    Process,
    Activity,
    Skill,
    RoleAnalysis,
    Source,
    AnalysisRun,
    User,
    Session,
]

_client: AsyncIOMotorClient | None = None


async def init_db(settings: Settings) -> None:
    """Create the Motor client and initialise Beanie documents/indexes."""
    global _client
    try:
        _client = AsyncIOMotorClient(
            settings.mongodb_url,
            serverSelectionTimeoutMS=settings.mongodb_timeout_ms,
        )
        await init_beanie(
            database=_client[settings.mongodb_database],  # type: ignore[arg-type]
            document_models=DOCUMENT_MODELS,
            allow_index_dropping=False,
        )
    except Exception:
        logger.exception("Failed to initialise MongoDB connection")
        raise
    logger.info("MongoDB initialised", extra={"extra_fields": {"database": settings.mongodb_database}})


async def close_db() -> None:
    """Close the Mongo client on shutdown."""
    global _client
    if _client is not None:
        _client.close()
        _client = None


async def ping_db() -> float:
    """Return server round-trip latency in ms, raising DatabaseError on failure."""
    if _client is None:
        raise DatabaseError("Database client is not initialised")
    try:
        started = await _client.admin.command("ping")
    except Exception as exc:
        logger.error("MongoDB ping failed: %s", exc)
        raise DatabaseError("Database is unreachable") from exc
    return float(started.get("ok", 0))  # type: ignore[union-attr]


async def get_database_client() -> AsyncIterator[AsyncIOMotorClient]:
    """FastAPI dependency exposing the active Motor client."""
    if _client is None:
        raise DatabaseError("Database client is not initialised")
    yield _client