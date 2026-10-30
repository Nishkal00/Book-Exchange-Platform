from datetime import UTC, datetime, timedelta

import jwt
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import get_db
from app.main import app
from app.models import User


def create_profile_user(db):
    user = User(
        name="Profile Student",
        email="profile@example.edu",
        password_hash="test_password_hash",
        role="student",
        department="CSE",
        location="Bengaluru",
        active=True,
        token_version=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_profile_token(user):
    settings = get_settings()
    expires_at = datetime.now(UTC) + timedelta(minutes=30)

    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "ver": user.token_version,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm="HS256",
    )


def setup_client(db):
    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    return TestClient(app)


def test_get_my_profile_success(db):
    user = create_profile_user(db)
    token = create_profile_token(user)
    client = setup_client(db)

    try:
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200

        body = response.json()
        assert body["id"] == user.id
        assert body["name"] == "Profile Student"
        assert body["email"] == "profile@example.edu"
        assert body["department"] == "CSE"
        assert body["location"] == "Bengaluru"
        assert body["role"] == "student"

        assert "password_hash" not in body
        assert "active" not in body

    finally:
        app.dependency_overrides.clear()


def test_get_my_profile_requires_authentication(db):
    client = setup_client(db)

    try:
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    finally:
        app.dependency_overrides.clear()


def test_update_my_profile_success_and_persistence(db):
    user = create_profile_user(db)
    token = create_profile_token(user)
    client = setup_client(db)

    try:
        response = client.patch(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Updated Student",
                "department": "AIML",
                "location": "PES University",
            },
        )

        assert response.status_code == 200

        body = response.json()
        assert body["name"] == "Updated Student"
        assert body["department"] == "AIML"
        assert body["location"] == "PES University"

        # Verify that changes persist in a subsequent GET.
        get_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert get_response.status_code == 200
        assert get_response.json()["name"] == "Updated Student"
        assert get_response.json()["department"] == "AIML"
        assert get_response.json()["location"] == "PES University"

    finally:
        app.dependency_overrides.clear()


def test_update_my_profile_allows_partial_update(db):
    user = create_profile_user(db)
    token = create_profile_token(user)
    client = setup_client(db)

    try:
        response = client.patch(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            json={"department": "Computer Science"},
        )

        assert response.status_code == 200
        assert response.json()["department"] == "Computer Science"
        assert response.json()["name"] == "Profile Student"
        assert response.json()["location"] == "Bengaluru"

    finally:
        app.dependency_overrides.clear()


def test_update_my_profile_rejects_protected_fields(db):
    user = create_profile_user(db)
    token = create_profile_token(user)
    client = setup_client(db)

    protected_payloads = [
        {"email": "changed@example.edu"},
        {"role": "admin"},
        {"active": False},
        {"password_hash": "new_hash"},
    ]

    try:
        for payload in protected_payloads:
            response = client.patch(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
            )

            assert response.status_code == 422

        db.refresh(user)

        assert user.email == "profile@example.edu"
        assert user.role == "student"
        assert user.active is True
        assert user.password_hash == "test_password_hash"

    finally:
        app.dependency_overrides.clear()


def test_update_my_profile_rejects_empty_payload(db):
    user = create_profile_user(db)
    token = create_profile_token(user)
    client = setup_client(db)

    try:
        response = client.patch(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            json={},
        )

        assert response.status_code == 422

    finally:
        app.dependency_overrides.clear()


def test_update_my_profile_rejects_invalid_values(db):
    user = create_profile_user(db)
    token = create_profile_token(user)
    client = setup_client(db)

    invalid_payloads = [
        {"name": ""},
        {"name": None},
        {"name": "A" * 101},
        {"department": "D" * 101},
        {"location": ""},
        {"location": "L" * 101},
        {"location": None},
    ]

    try:
        for payload in invalid_payloads:
            response = client.patch(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
            )

            assert response.status_code == 422

    finally:
        app.dependency_overrides.clear()
