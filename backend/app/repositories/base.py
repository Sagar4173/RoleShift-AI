"""Generic repository base class."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from beanie import Document, PydanticObjectId
from pymongo import ASCENDING, DESCENDING

from app.core.exceptions import DatabaseError
from app.core.logging import get_logger

ModelType = TypeVar("ModelType", bound=Document)

logger = get_logger("repositories.base")

_SORT_DIRECTIONS: dict[int, Any] = {1: ASCENDING, -1: DESCENDING}


class BaseRepository(Generic[ModelType]):
    """CRUD primitives shared by all repositories."""

    model: type[ModelType]

    async def create(self, document: ModelType) -> ModelType:
        try:
            await document.insert()
            return document
        except Exception as exc:
            logger.error("Failed to insert %s: %s", self.model.__name__, exc)
            raise DatabaseError(f"Failed to persist {self.model.__name__.lower()}") from exc

    async def get_by_id(self, document_id: PydanticObjectId) -> ModelType | None:
        try:
            return await self.model.get(document_id)
        except Exception as exc:
            logger.error("Failed to fetch %s %s: %s", self.model.__name__, document_id, exc)
            raise DatabaseError(f"Failed to read {self.model.__name__.lower()}") from exc

    async def list(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        filters: dict[str, Any] | None = None,
        sort: tuple[str, int] | None = None,
    ) -> list[ModelType]:
        """List documents, optionally filtered by exact field matches."""
        query = self.model.find(filters or {}).skip(skip).limit(limit)
        if sort is not None:
            query = query.sort((sort[0], _SORT_DIRECTIONS[sort[1]]))
        try:
            return await query.to_list()
        except Exception as exc:
            logger.error("Failed to list %s: %s", self.model.__name__, exc)
            raise DatabaseError(f"Failed to list {self.model.__name__.lower()}s") from exc

    async def count(self, filters: dict[str, Any] | None = None) -> int:
        try:
            return await self.model.find(filters or {}).count()
        except Exception as exc:
            logger.error("Failed to count %s: %s", self.model.__name__, exc)
            raise DatabaseError(f"Failed to count {self.model.__name__.lower()}s") from exc

    async def update(self, document: ModelType) -> ModelType:
        document.touch()
        try:
            await document.save()
            return document
        except Exception as exc:
            logger.error("Failed to update %s %s: %s", self.model.__name__, document.id, exc)
            raise DatabaseError(f"Failed to update {self.model.__name__.lower()}") from exc

    async def delete(self, document: ModelType) -> None:
        try:
            await document.delete()
        except Exception as exc:
            logger.error("Failed to delete %s %s: %s", self.model.__name__, document.id, exc)
            raise DatabaseError(f"Failed to delete {self.model.__name__.lower()}") from exc