from datetime import UTC, datetime

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.main import app
from app.models import Notification, User
from app.services.notifications import create_notification


def create_user(
    db: Session,
    email: str,
    name: str = "Test Student",
) -> User:
    user = User(
        name=name,
        email=email.lower(),
        password_hash="test_hash",
        role="student",
        active=True,
        token_version=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_token(user: User) -> str:
    settings = get_settings()

    return jwt.encode(
        {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
            "ver": user.token_version,
            "exp": datetime.now(UTC).timestamp() + 1800,
        },
        settings.jwt_secret,
        algorithm="HS256",
    )


@pytest.fixture
def client(db: Session):
    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def add_notification(
    db: Session,
    user_id: int,
    event_key: str,
    event_type: str = "MATCH_FOUND",
    message: str = "A new match was found.",
) -> None:
    create_notification(
        db,
        user_id=user_id,
        event_key=event_key,
        event_type=event_type,
        message=message,
    )
    db.commit()


def test_tc_not_01_user_can_list_own_notifications(
    client: TestClient,
    db: Session,
):
    user = create_user(db, "student1@stu.pes.edu")
    add_notification(db, user.id, "match:1:found")
    add_notification(
        db,
        user.id,
        "match:2:found",
        message="Another match was found.",
    )

    response = client.get(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {create_token(user)}"},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 2
    assert data["unread_count"] == 2
    assert len(data["items"]) == 2


def test_tc_not_01_notifications_are_isolated_between_users(
    client: TestClient,
    db: Session,
):
    user1 = create_user(db, "student1@stu.pes.edu")
    user2 = create_user(db, "student2@stu.pes.edu")

    add_notification(db, user1.id, "match:1:found")
    add_notification(db, user2.id, "match:2:found")

    response = client.get(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {create_token(user1)}"},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["message"] == "A new match was found."


def test_tc_not_01_unread_count_excludes_read_notifications(
    client: TestClient,
    db: Session,
):
    user = create_user(db, "student1@stu.pes.edu")

    add_notification(db, user.id, "match:1:found")
    add_notification(db, user.id, "match:2:found")

    notification = (
        db.query(Notification)
        .filter_by(
            user_id=user.id,
            event_key="match:1:found",
        )
        .one()
    )

    notification.is_read = True
    db.commit()

    response = client.get(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {create_token(user)}"},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert response.json()["unread_count"] == 1


def test_tc_not_01_user_can_mark_own_notification_as_read(
    client: TestClient,
    db: Session,
):
    user = create_user(db, "student1@stu.pes.edu")
    add_notification(db, user.id, "match:1:found")

    notification = (
        db.query(Notification)
        .filter_by(
            user_id=user.id,
        )
        .one()
    )

    response = client.patch(
        f"/api/v1/notifications/{notification.id}/read",
        headers={"Authorization": f"Bearer {create_token(user)}"},
    )

    assert response.status_code == 200
    assert response.json()["is_read"] is True

    db.refresh(notification)
    assert notification.is_read is True


def test_tc_not_01_user_cannot_mark_another_users_notification_as_read(
    client: TestClient,
    db: Session,
):
    user1 = create_user(db, "student1@stu.pes.edu")
    user2 = create_user(db, "student2@stu.pes.edu")

    add_notification(db, user2.id, "match:2:found")

    notification = (
        db.query(Notification)
        .filter_by(
            user_id=user2.id,
        )
        .one()
    )

    response = client.patch(
        f"/api/v1/notifications/{notification.id}/read",
        headers={"Authorization": f"Bearer {create_token(user1)}"},
    )

    assert response.status_code == 404

    db.refresh(notification)
    assert notification.is_read is False


def test_tc_not_01_unauthenticated_user_cannot_list_notifications(
    client: TestClient,
):
    response = client.get("/api/v1/notifications")

    assert response.status_code == 401


def test_tc_not_01_reprocessing_event_does_not_duplicate_notification(
    db: Session,
):
    user = create_user(db, "student1@stu.pes.edu")

    add_notification(db, user.id, "match:1:found")
    add_notification(db, user.id, "match:1:found")

    notifications = (
        db.query(Notification).filter_by(user_id=user.id, event_key="match:1:found").all()
    )

    assert len(notifications) == 1
