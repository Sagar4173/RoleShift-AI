"""Domain exceptions mapped to consistent HTTP error responses."""

from __future__ import annotations


class AppError(Exception):
    """Base class for expected application errors.

    ``code`` is a stable machine-readable identifier; ``status_code`` maps
    to the HTTP response status. Internal details are logged server-side and
    never returned to clients.
    """

    status_code: int = 500
    code: str = "internal_error"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        status_code: int | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        self.headers = headers


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ValidationError(AppError):
    status_code = 422
    code = "validation_error"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class DatabaseError(AppError):
    status_code = 503
    code = "database_unavailable"