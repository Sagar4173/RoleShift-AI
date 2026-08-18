"""Rate limiting tests (Phase 6.5.2).

A dedicated app fixture runs with deliberately small limits so a handful of
requests deterministically trips HTTP 429. The limiter reads time through
the ``app.core.rate_limit._monotonic`` test seam, so window expiry can be
simulated without sleeping.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from unittest.mock import AsyncMock, patch

import pytest
from beanie import init_beanie
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

import app.core.rate_limit as rate_limit_module
from app.core import database
from app.core.config import Settings
from app.main import create_app
from tests.conftest import seed_default_organization
from tests.test_analysis import MOCK_AI_RESULT

PASSWORD = "Str0ng!Password"

ANALYZE_NEW_PAYLOAD = {
    "name": "Data Engineer",
    "description": "Builds pipelines",
    "industry": "Technology",
    "processes": [{"name": "Data Processing", "activities": ["Data Collection"]}],
    "current_skills": ["Data Analysis"],
}


def _register(client: TestClient, email: str = "user@roleshift.local") -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "display_name": email.split("@")[0].title(), "password": PASSWORD},
    )
    assert response.status_code == 201, response.text


def _create_role(client: TestClient, name: str = "Data Analyst") -> str:
    response = client.post("/api/v1/roles", json={"name": name, "industry": "Technology"})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _create_role_context(client: TestClient, role_id: str) -> None:
    process = client.post(
        "/api/v1/processes", json={"name": "Data Processing", "description": "Test process"}
    )
    assert process.status_code == 201, process.text
    activity = client.post(
        "/api/v1/activities",
        json={
            "process_id": process.json()["id"],
            "role_id": role_id,
            "name": "Data Collection",
            "description": "Collect data",
            "current_human_involvement": "full",
            "sequence": 1,
        },
    )
    assert activity.status_code == 201, activity.text
    skills = client.put(
        f"/api/v1/roles/{role_id}/current-skills", json={"skills": ["Data Analysis"]}
    )
    assert skills.status_code == 200, skills.text


def _mock_provider() -> AsyncMock:
    provider = AsyncMock()
    provider.name = "deepseek"
    provider.analyze_role.return_value = MOCK_AI_RESULT
    return provider


@pytest.fixture
def rate_client(monkeypatch) -> Iterator[TestClient]:
    """App with small fixed-window limits so tests trip 429 quickly."""
    mock_client = AsyncMongoMockClient()

    async def _init_db(settings: Settings) -> None:
        await init_beanie(
            database=mock_client["roleshift_test"],
            document_models=database.DOCUMENT_MODELS,
        )
        await seed_default_organization(mock_client)
        database._client = mock_client

    async def _close_db() -> None:
        pass

    async def _ping_db() -> float:
        return 1.0

    monkeypatch.setattr(database, "init_db", _init_db)
    monkeypatch.setattr(database, "close_db", _close_db)
    monkeypatch.setattr(database, "ping_db", _ping_db)

    app = create_app(
        Settings(
            app_env="test",
            log_level="WARNING",
            ai_provider="none",
            ai_model="deepseek-chat",
            ai_api_key="",
            ollama_api_key="",
            ai_api_base_url="https://api.deepseek.com",
            ai_timeout_seconds=60,
            ai_temperature=0.3,
            rate_limit_login_per_minute=3,
            rate_limit_register_per_minute=3,
            rate_limit_analyze_per_hour=2,
            rate_limit_analyze_new_per_hour=2,
            rate_limit_skills_update_per_minute=2,
            rate_limit_member_mutation_per_minute=2,
            rate_limit_role_create_per_minute=2,
            rate_limit_role_delete_per_minute=2,
            rate_limit_skill_create_per_minute=2,
        )
    )
    with TestClient(app) as test_client:
        yield test_client


def _assert_429(response) -> None:
    assert response.status_code == 429
    assert response.json() == {
        "detail": {
            "code": "rate_limited",
            "message": "Too many requests. Please retry later.",
        }
    }
    assert int(response.headers["Retry-After"]) >= 1


# ------------------------------------------------------------------ register


def test_register_allows_three_then_rejects_with_429(rate_client: TestClient) -> None:
    for i in range(3):
        _register(rate_client, f"user{i}@roleshift.local")
    _assert_429(rate_client.post(
        "/api/v1/auth/register",
        json={"email": "user3@roleshift.local", "display_name": "U", "password": PASSWORD},
    ))


# ---------------------------------------------------------------------- login


def test_login_limited_then_recovers_after_window(rate_client: TestClient, monkeypatch) -> None:
    _register(rate_client)
    for _ in range(3):
        ok = rate_client.post(
            "/api/v1/auth/login",
            json={"email": "user@roleshift.local", "password": PASSWORD},
        )
        assert ok.status_code == 200, ok.text
    _assert_429(rate_client.post(
        "/api/v1/auth/login",
        json={"email": "user@roleshift.local", "password": PASSWORD},
    ))
    # Advance the clock past the 60-second window: the limit resets and
    # legitimate requests succeed again (bounded throttling, no lockout).
    monkeypatch.setattr(rate_limit_module, "_monotonic", lambda: time.monotonic() + 61)
    recovered = rate_client.post(
        "/api/v1/auth/login",
        json={"email": "user@roleshift.local", "password": PASSWORD},
    )
    assert recovered.status_code == 200, recovered.text


# ------------------------------------------------------ analyze (AI, critical)


def test_analyze_rejected_after_limit_without_provider_call(
    rate_client: TestClient, monkeypatch
) -> None:
    _register(rate_client)
    role_id = _create_role(rate_client)
    _create_role_context(rate_client, role_id)

    provider = _mock_provider()
    with patch("app.services.analysis_service.get_provider", return_value=provider):
        first = rate_client.post(f"/api/v1/roles/{role_id}/analyze", json={})
        assert first.status_code == 200, first.text
        # Deduplicated re-analysis returns the cached result without a
        # provider call but still counts against the limit.
        second = rate_client.post(f"/api/v1/roles/{role_id}/analyze", json={})
        assert second.status_code == 200, second.text
        third = rate_client.post(f"/api/v1/roles/{role_id}/analyze", json={})
        _assert_429(third)
    # The provider was invoked exactly once: the dedup hit and the
    # rate-limited request never reached the handler (no AnalysisRun, no
    # provider spend on rejection).
    assert provider.analyze_role.call_count == 1


# ------------------------------------------------- analyze-new (AI, critical)


def test_analyze_new_rejected_after_limit_without_provider_call(
    rate_client: TestClient, monkeypatch
) -> None:
    _register(rate_client)

    provider = _mock_provider()
    with patch("app.services.analysis_service.get_provider", return_value=provider):
        first = rate_client.post("/api/v1/roles/analyze-new", json=ANALYZE_NEW_PAYLOAD)
        assert first.status_code == 201, first.text
        second = rate_client.post("/api/v1/roles/analyze-new", json=ANALYZE_NEW_PAYLOAD)
        assert second.status_code == 201, second.text
        third = rate_client.post("/api/v1/roles/analyze-new", json=ANALYZE_NEW_PAYLOAD)
        _assert_429(third)
    assert provider.analyze_role.call_count == 2


# ---------------------------------------------------- current-skills (HIGH)


def test_current_skills_limited_after_two_updates(rate_client: TestClient) -> None:
    _register(rate_client)
    role_id = _create_role(rate_client)
    for _ in range(2):
        ok = rate_client.put(
            f"/api/v1/roles/{role_id}/current-skills", json={"skills": ["Data Analysis"]}
        )
        assert ok.status_code == 200, ok.text
    _assert_429(rate_client.put(
        f"/api/v1/roles/{role_id}/current-skills", json={"skills": ["Data Analysis"]}
    ))


# --------------------------------------------------- member mutations (HIGH)


def test_member_mutation_limited_after_two_changes(rate_client: TestClient) -> None:
    # Separate clients: each register overwrites the shared cookie jar with
    # its own session, so one client per user keeps every session distinct.
    app = rate_client.app
    owner = TestClient(app)
    user2 = TestClient(app)
    user3 = TestClient(app)
    try:
        _register(owner, "owner@roleshift.local")
        _register(user2, "user2@roleshift.local")
        _register(user3, "user3@roleshift.local")

        roster = owner.get("/api/v1/organizations/members")
        assert roster.status_code == 200, roster.text
        by_email = {m["email"]: m["user_id"] for m in roster.json()["items"]}
        assert {"owner@roleshift.local", "user2@roleshift.local", "user3@roleshift.local"} <= set(
            by_email
        )

        for _ in range(2):
            ok = owner.put(
                f"/api/v1/organizations/members/{by_email['user2@roleshift.local']}",
                json={"role": "analyst"},
            )
            assert ok.status_code == 200, ok.text
        _assert_429(owner.put(
            f"/api/v1/organizations/members/{by_email['user3@roleshift.local']}",
            json={"role": "analyst"},
        ))
    finally:
        owner.close()
        user2.close()
        user3.close()


# -------------------------------------------------- identity keying (X-Forwarded-For)


def test_rate_limit_keyed_by_forwarded_for_client_ip(rate_client: TestClient) -> None:
    """Clients behind a shared proxy are keyed by their real IP (the last
    X-Forwarded-For value), so they do not share a bucket."""
    for i in range(3):
        ok = rate_client.post(
            "/api/v1/auth/register",
            json={
                "email": f"user{i}@roleshift.local",
                "display_name": "U",
                "password": PASSWORD,
            },
            headers={"X-Forwarded-For": "10.0.0.0"},
        )
        assert ok.status_code == 201, ok.text
    # Fourth register from the same client IP is limited...
    _assert_429(rate_client.post(
        "/api/v1/auth/register",
        json={"email": "user4@roleshift.local", "display_name": "U", "password": PASSWORD},
        headers={"X-Forwarded-For": "10.0.0.0"},
    ))
    # ...but a different client IP is unaffected.
    other = rate_client.post(
        "/api/v1/auth/register",
        json={"email": "other@roleshift.local", "display_name": "O", "password": PASSWORD},
        headers={"X-Forwarded-For": "10.9.9.9"},
    )
    assert other.status_code == 201, other.text