"""Authentication tests: registration, login, sessions, and API protection."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi.testclient import TestClient

from app.models.session import Session
from app.models.user import User
from app.services.auth.security import hash_token

VALID_REGISTRATION = {
    "email": "alice@example.com",
    "display_name": "Alice Analyst",
    "password": "CorrectHorse99!",
}


def run_async(coro) -> Any:
    """Run a coroutine on a fresh loop for direct database assertions."""
    return asyncio.run(coro)


async def _fetch_user(email: str) -> User | None:
    return await User.find_one(User.email == email)


# ---------------------------------------------------------------- register


def test_register_creates_user_and_session(anon_client: TestClient) -> None:
    response = anon_client.post("/api/v1/auth/register", json=VALID_REGISTRATION)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "alice@example.com"
    assert body["display_name"] == "Alice Analyst"
    assert "password" not in response.text
    assert "password_hash" not in response.text
    cookie = response.cookies.get("roleshift_session")
    assert cookie, "session cookie must be set on registration"


def test_register_rejects_duplicate_email(anon_client: TestClient) -> None:
    assert anon_client.post("/api/v1/auth/register", json=VALID_REGISTRATION).status_code == 201
    response = anon_client.post("/api/v1/auth/register", json=VALID_REGISTRATION)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "email_exists"


def test_register_rejects_duplicate_email_case_insensitively(anon_client: TestClient) -> None:
    assert anon_client.post("/api/v1/auth/register", json=VALID_REGISTRATION).status_code == 201
    duplicate = {**VALID_REGISTRATION, "email": "Alice@Example.com"}
    response = anon_client.post("/api/v1/auth/register", json=duplicate)
    assert response.status_code == 409


def test_register_validates_email_format(anon_client: TestClient) -> None:
    response = anon_client.post(
        "/api/v1/auth/register",
        json={**VALID_REGISTRATION, "email": "not-an-email"},
    )
    assert response.status_code == 422


def test_register_rejects_short_password(anon_client: TestClient) -> None:
    response = anon_client.post(
        "/api/v1/auth/register",
        json={**VALID_REGISTRATION, "password": "short"},
    )
    assert response.status_code == 422


def test_register_rejects_unknown_fields(anon_client: TestClient) -> None:
    response = anon_client.post(
        "/api/v1/auth/register",
        json={**VALID_REGISTRATION, "is_admin": True},
    )
    assert response.status_code == 422


def test_password_stored_hashed_not_plaintext(anon_client: TestClient) -> None:
    anon_client.post("/api/v1/auth/register", json=VALID_REGISTRATION)
    user = run_async(_fetch_user("alice@example.com"))
    assert user is not None
    assert user.password_hash != "CorrectHorse99!"
    assert "CorrectHorse99!" not in user.password_hash
    assert user.password_hash.startswith("scrypt$")
    assert len(user.password_hash) > 40


# ---------------------------------------------------------------- login


def test_login_succeeds_with_valid_credentials(anon_client: TestClient) -> None:
    anon_client.post("/api/v1/auth/register", json=VALID_REGISTRATION)
    response = anon_client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "CorrectHorse99!"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "alice@example.com"
    assert response.cookies.get("roleshift_session")


def test_login_accepts_normalized_email(anon_client: TestClient) -> None:
    anon_client.post("/api/v1/auth/register", json=VALID_REGISTRATION)
    response = anon_client.post(
        "/api/v1/auth/login",
        json={"email": "  ALICE@example.com ", "password": "CorrectHorse99!"},
    )
    assert response.status_code == 200


def test_login_rejects_invalid_password(anon_client: TestClient) -> None:
    anon_client.post("/api/v1/auth/register", json=VALID_REGISTRATION)
    response = anon_client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "WrongPassword1"},
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_credentials"


def test_login_rejects_unknown_email(anon_client: TestClient) -> None:
    response = anon_client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "Whatever123"},
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_credentials"


def test_login_rejects_disabled_user(anon_client: TestClient) -> None:
    anon_client.post("/api/v1/auth/register", json=VALID_REGISTRATION)
    user = run_async(_fetch_user("alice@example.com"))
    assert user is not None
    user.is_active = False
    run_async(user.save())
    response = anon_client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "CorrectHorse99!"},
    )
    assert response.status_code == 401


def test_session_cookie_is_http_only_and_lax(anon_client: TestClient) -> None:
    response = anon_client.post("/api/v1/auth/register", json=VALID_REGISTRATION)
    set_cookie = response.headers.get("set-cookie", "").lower()
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie
    assert "roleshift_session=" in set_cookie


# ---------------------------------------------------------------- me


def test_me_returns_current_user(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "tester@roleshift.local"
    assert body["display_name"] == "Test User"


def test_me_requires_authentication(anon_client: TestClient) -> None:
    assert anon_client.get("/api/v1/auth/me").status_code == 401


# ---------------------------------------------------------------- protection


def test_protected_endpoints_reject_anonymous(anon_client: TestClient) -> None:
    for method, path in [
        ("GET", "/api/v1/roles"),
        ("POST", "/api/v1/roles"),
        ("GET", "/api/v1/roles/compare"),
        ("POST", "/api/v1/roles/analyze-new"),
        ("GET", "/api/v1/processes"),
        ("GET", "/api/v1/activities"),
        ("GET", "/api/v1/skills"),
        ("GET", "/api/v1/organizations"),
        ("GET", "/api/v1/dashboard/summary"),
        ("GET", "/api/v1/dashboard/skills"),
    ]:
        response = anon_client.request(method, path)
        assert response.status_code == 401, f"{method} {path} must require auth"
        assert response.json()["detail"]["code"] == "unauthorized"


def test_protected_endpoint_succeeds_authenticated(client: TestClient) -> None:
    response = client.get("/api/v1/roles")
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_health_endpoints_remain_public(anon_client: TestClient) -> None:
    assert anon_client.get("/health").status_code == 200
    assert anon_client.get("/health/db").status_code == 200


# ---------------------------------------------------------------- sessions


def test_invalid_session_token_rejected(anon_client: TestClient) -> None:
    anon_client.cookies.set("roleshift_session", "forged-token-value")
    assert anon_client.get("/api/v1/auth/me").status_code == 401
    assert anon_client.get("/api/v1/roles").status_code == 401


def test_expired_session_rejected(anon_client: TestClient) -> None:
    anon_client.post("/api/v1/auth/register", json=VALID_REGISTRATION)
    user = run_async(_fetch_user("alice@example.com"))
    assert user is not None
    expired = Session(
        user_id=user.id,
        token_hash=hash_token("expired-token"),
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    run_async(expired.insert())
    anon_client.cookies.set("roleshift_session", "expired-token")
    response = anon_client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_logout_revokes_session(client: TestClient) -> None:
    assert client.get("/api/v1/auth/me").status_code == 200
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/roles").status_code == 401


def test_logout_is_idempotent(anon_client: TestClient) -> None:
    assert anon_client.post("/api/v1/auth/logout").status_code == 204