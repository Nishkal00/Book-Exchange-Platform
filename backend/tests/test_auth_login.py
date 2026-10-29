from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import get_db
from app.main import app
from app.models import User
from app.routers.auth import get_current_user


@pytest.fixture
def client(db):
    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def user(db):
    account = User(
        name="Test Student",
        email="student@example.edu",
        password_hash=bcrypt.hashpw(b"SecurePass123", bcrypt.gensalt()).decode("utf-8"),
        role="student",
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def test_login_success_returns_30_minute_jwt(client, user, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "jwt_secret", "test-secret-for-auth-tests-at-least-32-bytes")
    monkeypatch.setattr(settings, "jwt_expire_minutes", 30)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "SecurePass123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expiresIn"] == 1800
    assert body["user"]["email"] == user.email

    claims = jwt.decode(
        body["access_token"],
        settings.jwt_secret,
        algorithms=["HS256"],
    )
    assert claims["sub"] == str(user.id)
    assert claims["ver"] == user.token_version
    assert claims["exp"] > datetime.now(UTC).timestamp()


@pytest.mark.parametrize(
    "email,password",
    [
        ("unknown@example.edu", "SecurePass123"),
        ("student@example.edu", "WrongPass123"),
    ],
)
def test_login_invalid_credentials_are_identical(client, user, monkeypatch, email, password):
    monkeypatch.setattr(
        get_settings(), "jwt_secret", "test-secret-for-auth-tests-at-least-32-bytes"
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert response.json()["error"]["message"] == "Invalid email or password."


def test_login_rejects_inactive_user(client, user, monkeypatch):
    monkeypatch.setattr(
        get_settings(), "jwt_secret", "test-secret-for-auth-tests-at-least-32-bytes"
    )
    user.active = False

    response = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "SecurePass123"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_get_current_user_rejects_expired_token(db, user, monkeypatch):
    monkeypatch.setattr(
        get_settings(), "jwt_secret", "test-secret-for-auth-tests-at-least-32-bytes"
    )
    token = jwt.encode(
        {
            "sub": str(user.id),
            "exp": datetime.now(UTC) - timedelta(minutes=1),
            "ver": user.token_version,
        },
        get_settings().jwt_secret,
        algorithm="HS256",
    )

    class Credentials:
        scheme = "Bearer"
        credentials = token

    with pytest.raises(HTTPException) as exc:
        get_current_user(credentials=Credentials(), db=db)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Token has expired"


def test_get_current_user_rejects_wrong_token_version(db, user, monkeypatch):
    monkeypatch.setattr(
        get_settings(), "jwt_secret", "test-secret-for-auth-tests-at-least-32-bytes"
    )
    token = jwt.encode(
        {
            "sub": str(user.id),
            "exp": datetime.now(UTC) + timedelta(minutes=30),
            "ver": user.token_version + 1,
        },
        get_settings().jwt_secret,
        algorithm="HS256",
    )

    class Credentials:
        scheme = "Bearer"
        credentials = token

    with pytest.raises(HTTPException) as exc:
        get_current_user(credentials=Credentials(), db=db)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Token has been revoked"


def test_get_current_user_rejects_missing_token_version(db, user, monkeypatch):
    monkeypatch.setattr(
        get_settings(), "jwt_secret", "test-secret-for-auth-tests-at-least-32-bytes"
    )
    token = jwt.encode(
        {
            "sub": str(user.id),
            "exp": datetime.now(UTC) + timedelta(minutes=30),
        },
        get_settings().jwt_secret,
        algorithm="HS256",
    )

    class Credentials:
        scheme = "Bearer"
        credentials = token

    with pytest.raises(HTTPException) as exc:
        get_current_user(credentials=Credentials(), db=db)

    assert exc.value.status_code == 401
