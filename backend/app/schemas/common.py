"""Shared schema primitives: error responses, pagination, object IDs."""

from __future__ import annotations

from typing import Annotated, Generic, TypeVar

from beanie import PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field

ObjectIdStr = PydanticObjectId

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=2000)


class ErrorResponse(BaseModel):
    detail: ErrorDetail

    model_config = ConfigDict(extra="forbid")


class PageMeta(BaseModel):
    skip: int = Field(ge=0)
    limit: int = Field(ge=1)
    total: int = Field(ge=0)


class Page(BaseModel, Generic[T]):
    model_config = ConfigDict(extra="forbid")

    items: list[T]
    meta: PageMeta


def pagination_params(
    skip: Annotated[int, Field(ge=0)] = 0,
    limit: Annotated[int, Field(ge=1, le=100)] = 50,
) -> tuple[int, int]:
    """Shared pagination query parameters."""
    return skip, limit