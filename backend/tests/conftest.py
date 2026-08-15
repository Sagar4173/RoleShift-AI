"""Shared test fixtures.

The application is exercised end-to-end (HTTP layer) against an in-memory
MongoDB (mongomock-motor), so the test suite runs without a live database.
Production code paths are unchanged; only the database bootstrap functions
are swapped.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from beanie import init_beanie
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

from app.core import database
from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def client(monkeypatch) -> Iterator[TestClient]:
    """HTTP client with the real FastAPI app backed by an in-memory DB."""
    mock_client = AsyncMongoMockClient()

    async def _init_db(settings: Settings) -> None:
        await init_beanie(
            database=mock_client["roleshift_test"],  # type: ignore[arg-type]
            document_models=database.DOCUMENT_MODELS,
        )
        database._client = mock_client

    async def _close_db() -> None:
        pass

    async def _ping_db() -> float:
        return 1.0

    monkeypatch.setattr(database, "init_db", _init_db)
    monkeypatch.setattr(database, "close_db", _close_db)
    monkeypatch.setattr(database, "ping_db", _ping_db)

    # AI settings are pinned so tests are hermetic: they never inherit values
    # from a developer's .env and never reach a real provider. ai_provider="none"
    # yields NoopProvider (raises AIProviderNotConfiguredError), and tests that
    # exercise the pipeline mock get_provider directly.
    app = create_app(
        settings=Settings(
            app_env="test",
            log_level="WARNING",
            ai_provider="none",
            ai_model="deepseek-chat",
            ai_api_key="",
            ollama_api_key="",
            ai_api_base_url="https://api.deepseek.com",
            ai_timeout_seconds=60,
            ai_temperature=0.3,
        )
    )
    with TestClient(app) as test_client:
        yield test_client


def create_organization(client: TestClient, name: str = "Acme Corp") -> dict:
    response = client.post(
        "/api/v1/organizations",
        json={"name": name, "industry": "Technology", "description": "Test org"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_role(client: TestClient, organization_id: str, name: str = "Data Analyst") -> dict:
    response = client.post(
        "/api/v1/roles",
        json={"organization_id": organization_id, "name": name, "industry": "Technology"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_process(
    client: TestClient, organization_id: str, name: str = "Data Processing"
) -> dict:
    response = client.post(
        "/api/v1/processes",
        json={"organization_id": organization_id, "name": name, "description": "Test process"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_activity(
    client: TestClient,
    role_id: str,
    process_id: str,
    name: str,
    seq: int = 1,
) -> dict:
    response = client.post(
        "/api/v1/activities",
        json={
            "process_id": process_id,
            "role_id": role_id,
            "name": name,
            "description": f"{name} description",
            "current_human_involvement": "full",
            "sequence": seq,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def add_current_skills(client: TestClient, role_id: str, skills: list[str]) -> dict:
    """Link current skills onto a role by name (via the current-skills endpoint)."""
    response = client.put(
        f"/api/v1/roles/{role_id}/current-skills",
        json={"skills": skills},
    )
    assert response.status_code == 200, response.text
    return response.json()


def create_role_with_context(
    client: TestClient,
    organization_id: str,
    name: str = "Data Analyst",
    *,
    activities: list[tuple[str, str]] | None = None,
    skills: list[str] | None = None,
) -> dict:
    """Create a role plus a process, activities, and current skills.

    ``activities`` is a list of (process_name, activity_name) pairs; a
    process is created per unique process name. Defaults give the role one
    process with one activity and one current skill so analyze endpoints
    pass the context validation gate.
    """
    activities = activities or [("Data Processing", "Data Collection")]
    skills = skills or ["Data Analysis"]

    role = create_role(client, organization_id, name)

    processes_by_name: dict[str, str] = {}
    seq = 1
    for process_name, activity_name in activities:
        if process_name not in processes_by_name:
            proc = create_process(client, organization_id, process_name)
            processes_by_name[process_name] = proc["id"]
        create_activity(client, role["id"], processes_by_name[process_name], activity_name, seq)
        seq += 1

    add_current_skills(client, role["id"], skills)
    return role