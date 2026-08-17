"""Request validation tests: malformed input must be rejected cleanly."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_missing_required_fields_rejected(client: TestClient) -> None:
    response = client.post("/api/v1/roles", json={})
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "validation_error"


def test_unknown_fields_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/roles",
        json={"name": "Acme", "evil_field": "x"},
    )
    assert response.status_code == 422


def test_overlong_fields_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/roles",
        json={"name": "A" * 300},
    )
    assert response.status_code == 422


def test_invalid_role_status_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/roles",
        json={"name": "Analyst", "status": "frozen"},
    )
    assert response.status_code == 422


def test_client_supplied_organization_id_rejected(client: TestClient) -> None:
    """Phase 6.3: the organization always comes from the session, never the body."""
    response = client.post(
        "/api/v1/roles",
        json={
            "name": "Analyst",
            "organization_id": "507f1f77bcf86cd799439011",
        },
    )
    assert response.status_code == 422


def test_invalid_object_id_rejected(client: TestClient) -> None:
    response = client.get("/api/v1/organizations/not-an-id")
    assert response.status_code == 422


def test_invalid_activity_sequence_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/activities",
        json={
            "process_id": "507f1f77bcf86cd799439011",
            "role_id": "507f1f77bcf86cd799439011",
            "name": "Review",
            "sequence": -5,
        },
    )
    assert response.status_code == 422