"""ASGI middleware: security response headers and request body size limits.

- ``SecurityHeadersMiddleware`` stamps every HTTP response with hardening
  headers. ``Strict-Transport-Security`` is emitted only in production
  (HTTPS). The full restrictive CSP is applied to API responses (JSON —
  nothing is loaded, so nothing can break); non-API responses (dev docs,
  which load script/style from CDNs) receive a navigation-only policy.
- ``RequestSizeLimitMiddleware`` rejects request bodies larger than
  ``max_bytes`` with HTTP 413 — both via the declared Content-Length up
  front and by byte count while streaming (chunked) bodies are read.
"""

from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse
from starlette.datastructures import MutableHeaders
from starlette.types import Message, Receive, Scope, Send

MAX_BODY_BYTES = 1_048_576  # 1 MiB

# Strict CSP for API responses (JSON only): nothing is loaded from anywhere.
# frame-ancestors 'none' blocks clickjacking; base-uri/form-action harden
# against injection-driven navigations.
API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
# Navigation-only CSP for non-API responses (e.g. dev docs which load
# script/style from CDNs): protects framing and navigation without
# breaking those pages.
NAV_CSP = "frame-ancestors 'none'; base-uri 'none'; form-action 'none'; object-src 'none'"

_TOO_LARGE_BODY = {
    "detail": {
        "code": "payload_too_large",
        "message": "Request body exceeds the maximum allowed size",
    }
}


class RequestBodyTooLarge(Exception):
    """Internal signal: a streaming body exceeded the configured limit."""


class SecurityHeadersMiddleware:
    """Stamp security headers on every HTTP response."""

    def __init__(self, app: Any, *, app_env: str, api_prefix: str) -> None:
        self.app = app
        self.hsts = app_env == "production"
        self.api_prefix = api_prefix

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        csp = API_CSP if path.startswith(self.api_prefix) else NAV_CSP

        async def send_with_headers(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.append("X-Content-Type-Options", "nosniff")
                headers.append("Referrer-Policy", "strict-origin-when-cross-origin")
                headers.append("X-Frame-Options", "DENY")
                headers.append("Content-Security-Policy", csp)
                if self.hsts:
                    headers.append(
                        "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
                    )
            await send(message)

        await self.app(scope, receive, send_with_headers)


class RequestSizeLimitMiddleware:
    """Reject request bodies larger than ``max_bytes`` with HTTP 413."""

    def __init__(self, app: Any, max_bytes: int = MAX_BODY_BYTES) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        for name, value in scope.get("headers", []):
            if name == b"content-length":
                try:
                    declared = int(value)
                except ValueError:
                    break
                if declared > self.max_bytes:
                    await JSONResponse(status_code=413, content=_TOO_LARGE_BODY)(
                        scope, receive, send
                    )
                    return
                break

        received = 0

        async def guarded_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise RequestBodyTooLarge()
            return message

        try:
            await self.app(scope, guarded_receive, send)
        except RequestBodyTooLarge:
            await JSONResponse(status_code=413, content=_TOO_LARGE_BODY)(scope, receive, send)