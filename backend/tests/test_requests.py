
import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from tests.test_listings import create_auth_token, create_test_user


@pytest.fixture
def client(db):
    """TestClient with the test database injected."""

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_create_borrow_request_with_isbn(client, db):
    user = create_test_user(db)
    token = create_auth_token(user)

    response = client.post(
        "/api/v1/requests",
        json={"isbn": "9780131103627", "location": "Campus"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["isbn"] == "9780131103627"
    assert data["title_query"] is None
    assert data["location"] == "Campus"
    assert data["status"] == "OPEN"


def test_create_borrow_request_with_title(client, db):
    user = create_test_user(db)
    token = create_auth_token(user)

    response = client.post(
        "/api/v1/requests",
        json={"title_query": "Clean Code", "location": "Library"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    assert response.json()["title_query"] == "Clean Code"


def test_create_borrow_request_without_criterion_returns_422(client, db):
    user = create_test_user(db)
    token = create_auth_token(user)

    response = client.post(
        "/api/v1/requests",
        json={"location": "Campus"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


def test_create_borrow_request_with_both_criteria_returns_422(client, db):
    user = create_test_user(db)
    token = create_auth_token(user)

    response = client.post(
        "/api/v1/requests",
        json={
            "isbn": "9780131103627",
            "title_query": "Clean Code",
            "location": "Campus",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


def test_duplicate_active_borrow_request_returns_409(client, db):
    user = create_test_user(db)
    token = create_auth_token(user)
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"isbn": "9780131103627", "location": "Campus"}

    first = client.post("/api/v1/requests", json=payload, headers=headers)
    second = client.post("/api/v1/requests", json=payload, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 409


def test_create_borrow_request_requires_authentication(client):
    response = client.post(
        "/api/v1/requests",
        json={"title_query": "Clean Code", "location": "Campus"},
    )

    assert response.status_code == 401


def test_different_students_can_request_same_isbn(client, db):
    first_user = create_test_user(db, email="first@example.edu")
    second_user = create_test_user(db, email="second@example.edu")
    payload = {"isbn": "9780131103627", "location": "Campus"}

    first = client.post(
        "/api/v1/requests",
        json=payload,
        headers={
            "Authorization": f"Bearer {create_auth_token(first_user)}",
        },
    )
    second = client.post(
        "/api/v1/requests",
        json=payload,
        headers={
            "Authorization": f"Bearer {create_auth_token(second_user)}",
        },
    )

    assert first.status_code == 201
    assert second.status_code == 201
