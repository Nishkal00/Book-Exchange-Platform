from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import get_db
from app.main import app
from app.models import User

SECRET = "test-secret-for-auth-tests-at-least-32-bytes"
PASSWORD = "SecurePass123"


@pytest.fixture
def client(db, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "jwt_secret", SECRET)
    monkeypatch.setattr(settings, "jwt_expire_minutes", 30)

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def user(db):
    account = User(
        name="Test Student",
        email="logout@example.edu",
        password_hash=bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt()).decode("utf-8"),
        role="student",
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def login(client, email):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    return response.json()["access_token"]


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_tc_auth_05_logout_returns_204_and_revokes_existing_tokens(client, user):
    token = login(client, user.email)

    response = client.post("/api/v1/auth/logout", headers=bearer(token))
    assert response.status_code == 204
    assert response.content == b""

    # The same token must now be rejected on a protected endpoint.
    rejected = client.post("/api/v1/auth/logout", headers=bearer(token))
    assert rejected.status_code == 401
    assert rejected.json()["detail"] == "Token has been revoked"


def test_tc_auth_05_logout_revokes_every_token_issued_before_it(client, user):
    first = login(client, user.email)
    second = login(client, user.email)

    assert client.post("/api/v1/auth/logout", headers=bearer(second)).status_code == 204
    assert client.post("/api/v1/auth/logout", headers=bearer(first)).status_code == 401


def test_tc_auth_05_new_login_after_logout_issues_working_token(client, user):
    old = login(client, user.email)
    assert client.post("/api/v1/auth/logout", headers=bearer(old)).status_code == 204

    fresh = login(client, user.email)
    assert client.post("/api/v1/auth/logout", headers=bearer(fresh)).status_code == 204


def test_tc_auth_06_expired_token_returns_401(client, user):
    expired = jwt.encode(
        {
            "sub": str(user.id),
            "ver": user.token_version,
            "exp": datetime.now(UTC) - timedelta(minutes=1),
        },
        SECRET,
        algorithm="HS256",
    )

    response = client.post("/api/v1/auth/logout", headers=bearer(expired))
    assert response.status_code == 401
    assert response.json()["detail"] == "Token has expired"


def test_tc_auth_06_tampered_signature_returns_401(client, user):
    token = login(client, user.email)
    tampered = token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB")

    response = client.post("/api/v1/auth/logout", headers=bearer(tampered))
    assert response.status_code == 401


def test_tc_auth_06_wrong_secret_returns_401(client, user):
    forged = jwt.encode(
        {
            "sub": str(user.id),
            "ver": user.token_version,
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        "a-different-secret-that-is-also-long-enough-123",
        algorithm="HS256",
    )

    assert client.post("/api/v1/auth/logout", headers=bearer(forged)).status_code == 401


def test_tc_auth_06_version_mismatch_returns_401(client, user):
    stale = jwt.encode(
        {
            "sub": str(user.id),
            "ver": user.token_version + 5,
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        SECRET,
        algorithm="HS256",
    )

    response = client.post("/api/v1/auth/logout", headers=bearer(stale))
    assert response.status_code == 401
    assert response.json()["detail"] == "Token has been revoked"


def test_logout_without_token_returns_401(client):
    assert client.post("/api/v1/auth/logout").status_code == 401
