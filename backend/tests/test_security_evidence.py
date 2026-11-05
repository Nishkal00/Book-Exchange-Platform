"""API-level security evidence for the RTM (TC-SEC-01, 02, 03, 06 and TC-AUTH-02)."""

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import get_db
from app.main import app
from app.models import User
from app.routers import auth as auth_module


@pytest.fixture
def client(db, monkeypatch):
    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    monkeypatch.setattr(get_settings(), "allowed_email_domains", "example.edu")
    auth_module.login_rate_limiter._failures.clear()  # fresh limiter state per test
    yield TestClient(app)
    app.dependency_overrides.clear()
    auth_module.login_rate_limiter._failures.clear()


@pytest.fixture
def user(db):
    account = User(
        name="Sec Student",
        email="sec@example.edu",
        password_hash=bcrypt.hashpw(b"SecurePass123", bcrypt.gensalt()).decode(),
        role="student",
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def login(client, password):
    return client.post(
        "/api/v1/auth/login", json={"email": "sec@example.edu", "password": password}
    )


def register(client, **overrides):
    body = {"name": "New Student", "email": "new@example.edu", "password": "SecurePass123"}
    body.update(overrides)
    return client.post("/api/v1/auth/register", json=body)


def test_tc_sec_06_sixth_attempt_is_throttled_with_retry_after(client, user):
    for _ in range(5):
        assert login(client, "wrong-password").status_code == 401
    for password in ("wrong-password", "SecurePass123"):
        response = login(client, password)
        assert response.status_code == 429
        assert int(response.headers["Retry-After"]) > 0
        assert "access_token" not in response.text


def test_tc_sec_06_success_before_threshold_clears_failures(client, user):
    for _ in range(4):
        login(client, "wrong-password")
    assert login(client, "SecurePass123").status_code == 200
    for _ in range(4):
        assert login(client, "wrong-password").status_code == 401
    assert login(client, "SecurePass123").status_code == 200


def test_tc_sec_02_unsigned_none_algorithm_token_is_rejected(client, user):
    token = jwt.encode(
        {
            "sub": str(user.id),
            "ver": user.token_version,
            "exp": datetime.now(UTC) + timedelta(hours=1),
        },
        key=None,
        algorithm="none",
    )
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_tc_sec_02_missing_and_garbage_tokens_are_rejected(client, user):
    assert client.get("/api/v1/auth/me").status_code in (401, 403)
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
    assert response.status_code == 401


def test_tc_sec_02_inactive_user_token_is_rejected(client, user, db):
    token = login(client, "SecurePass123").json()["access_token"]
    user.active = False
    db.commit()
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_tc_sec_01_over_72_byte_password_is_rejected_and_hash_not_returned(client, db):
    response = register(client, password="A1" + "x" * 80)
    assert response.status_code == 422
    assert db.query(User).count() == 0

    ok = register(client)
    assert ok.status_code == 201
    assert "password" not in ok.text and "hash" not in ok.text
    stored = db.query(User).one()
    assert stored.password_hash.startswith("$2")
    assert "SecurePass123" not in stored.password_hash


def test_tc_auth_02_duplicate_domain_weak_password_and_empty_name(client, db):
    assert register(client).status_code == 201
    assert register(client, email="NEW@example.edu").status_code == 409
    assert register(client, email="x@gmail.com").status_code == 400
    assert register(client, email="weak@example.edu", password="short1").status_code == 422
    assert register(client, email="empty@example.edu", name="").status_code == 422
    assert db.query(User).count() == 1


def test_tc_sec_03_cors_allows_configured_origin_only(client):
    allowed = get_settings().cors_origin_list[0]
    ok = client.get("/health", headers={"Origin": allowed})
    assert ok.headers.get("access-control-allow-origin") == allowed
    bad = client.get("/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in bad.headers
