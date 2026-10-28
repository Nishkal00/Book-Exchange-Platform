import bcrypt
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import get_db
from app.main import app
from app.models import User


def test_registration_success(db, monkeypatch):
    monkeypatch.setattr(
        get_settings(),
        "allowed_email_domains",
        "example.edu",
    )

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    try:
        response = TestClient(app).post(
            "/api/v1/auth/register",
            json={
                "name": "Test Student",
                "email": "STUDENT@example.edu",
                "password": "SecurePass123",
            },
        )

        assert response.status_code == 201

        body = response.json()
        assert body["email"] == "student@example.edu"
        assert body["role"] == "student"
        assert set(body) == {
            "id",
            "name",
            "email",
            "role",
            "department",
            "location",
        }

        # Password and password hash must never appear in the response.
        assert "password" not in body
        assert "password_hash" not in body

        # Verify the password is stored as a bcrypt hash.
        user = db.query(User).filter_by(email="student@example.edu").one()

        assert user.password_hash != "SecurePass123"
        assert bcrypt.checkpw(
            b"SecurePass123",
            user.password_hash.encode("utf-8"),
        )

    finally:
        app.dependency_overrides.clear()


def test_registration_rejects_unapproved_domain(db, monkeypatch):
    monkeypatch.setattr(
        get_settings(),
        "allowed_email_domains",
        "example.edu",
    )

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    try:
        response = TestClient(app).post(
            "/api/v1/auth/register",
            json={
                "name": "Test Student",
                "email": "student@other.edu",
                "password": "SecurePass123",
            },
        )

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "INVALID_EMAIL_DOMAIN"

    finally:
        app.dependency_overrides.clear()


def test_registration_rejects_invalid_password():
    response = TestClient(app).post(
        "/api/v1/auth/register",
        json={
            "name": "Test Student",
            "email": "student@example.edu",
            "password": "short",
        },
    )

    assert response.status_code == 422
