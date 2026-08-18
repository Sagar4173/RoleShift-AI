"""In-memory fixed-window rate limiting.

Abuse-sensitive endpoints (authentication and AI analysis) are throttled
with bounded, non-permanent limits: a client that exceeds a limit receives
HTTP 429 with a ``Retry-After`` header and is allowed again once the
window elapses. No account is ever locked out, and the 429 response never
reveals internal details (limit values, identities, or stack traces).

Limitations (by design for the current single-instance deployment):
counters live in process memory, so limits are effective per application
instance and are NOT globally coordinated across multiple workers or
instances. Render's free tier runs a single uvicorn worker; scaling out
would require a shared store (e.g. Redis) instead.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable

from fastapi import Request

from app.core.config import Settings
from app.core.exceptions import AppError

WINDOW_MINUTE = 60
WINDOW_HOUR = 3600

# Test seam: the limiter reads time through this callable so tests can
# simulate window expiry without sleeping.
_monotonic: Callable[[], float] = time.monotonic


@dataclass(frozen=True)
class RateLimitPolicy:
    """A single fixed-window limit: at most ``limit`` requests per window."""

    key: str
    limit: int
    window_seconds: int


def build_policies(settings: Settings) -> dict[str, RateLimitPolicy]:
    """Derive the active rate-limit policies from application settings."""
    return {
        "login": RateLimitPolicy("login", settings.rate_limit_login_per_minute, WINDOW_MINUTE),
        "register": RateLimitPolicy("register", settings.rate_limit_register_per_minute, WINDOW_MINUTE),
        "analyze": RateLimitPolicy("analyze", settings.rate_limit_analyze_per_hour, WINDOW_HOUR),
        "analyze_new": RateLimitPolicy("analyze_new", settings.rate_limit_analyze_new_per_hour, WINDOW_HOUR),
        "current_skills": RateLimitPolicy("current_skills", settings.rate_limit_skills_update_per_minute, WINDOW_MINUTE),
        "member_mutation": RateLimitPolicy("member_mutation", settings.rate_limit_member_mutation_per_minute, WINDOW_MINUTE),
        "role_create": RateLimitPolicy("role_create", settings.rate_limit_role_create_per_minute, WINDOW_MINUTE),
        "role_delete": RateLimitPolicy("role_delete", settings.rate_limit_role_delete_per_minute, WINDOW_MINUTE),
        "skill_create": RateLimitPolicy("skill_create", settings.rate_limit_skill_create_per_minute, WINDOW_MINUTE),
    }


class InMemoryRateLimiter:
    """Thread-safe fixed-window counter keyed by (policy, identity).

    Buckets are created lazily and replaced once the window elapses, so
    memory use is proportional to the number of active identities and the
    limiter never accumulates unbounded state for idle keys.
    """

    def __init__(self, policies: dict[str, RateLimitPolicy]) -> None:
        self._policies = policies
        self._buckets: dict[tuple[str, str], tuple[float, int]] = {}
        self._lock = threading.Lock()

    def check(self, policy: str, identity: str) -> tuple[bool, int]:
        """Count one request against the policy.

        Returns ``(allowed, retry_after_seconds)``. When ``allowed`` is
        False, ``retry_after_seconds`` is the time until the window resets.
        """
        p = self._policies[policy]
        now = _monotonic()
        with self._lock:
            key = (policy, identity)
            window_start, count = self._buckets.get(key, (now, 0))
            if now - window_start >= p.window_seconds:
                window_start, count = now, 0
            if count >= p.limit:
                retry_after = max(1, int(p.window_seconds - (now - window_start)))
                return False, retry_after
            self._buckets[key] = (window_start, count + 1)
            return True, 0


def client_ip(request: Request) -> str:
    """Best-effort client identity.

    Uses the LAST ``X-Forwarded-For`` value (the address appended by the
    trusted proxy in front of the app — Render) so all clients behind the
    shared proxy address do not collapse into a single bucket. Falls back
    to the direct peer address (``testclient`` in the test suite).
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


def rate_limited_error(retry_after: int) -> AppError:
    """Build the 429 response: generic message, Retry-After header only.

    Deliberately leaks nothing about limits or identities; the window
    duration is only communicated through the standard Retry-After header.
    """
    return AppError(
        "Too many requests. Please retry later.",
        code="rate_limited",
        status_code=429,
        headers={"Retry-After": str(retry_after)},
    )