from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import AuditEvent, Exchange, Listing, User
from tests.test_listings import create_auth_token, create_test_user


@pytest.fixture
def client(db):
    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin(db):
    account = User(
        name="Test Admin",
        email="admin@example.edu",
        password_hash="hashed_pw_test",
        role="admin",
        location="Campus Center",
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def auth(user):
    return {"Authorization": f"Bearer {create_auth_token(user)}"}


def test_admin_can_deactivate_user(client, db, admin):
    target = create_test_user(db, email="target@example.edu")

    response = client.post(
        f"/api/v1/admin/users/{target.id}/deactivate",
        json={"reason": "Repeated abusive behaviour"},
        headers=auth(admin),
    )

    assert response.status_code == 200
    assert response.json()["active"] is False

    db.refresh(target)
    assert target.active is False
    assert target.token_version == 1

    audit = db.query(AuditEvent).one()
    assert audit.actor_id == admin.id
    assert audit.target == f"USER:{target.id}"
    assert audit.action == "USER_DEACTIVATED"
    assert audit.reason == "Repeated abusive behaviour"


def test_student_cannot_access_admin_endpoint(client, db):
    student = create_test_user(db, email="student-admin-test@example.edu")
    target = create_test_user(db, email="target-admin-test@example.edu")

    response = client.post(
        f"/api/v1/admin/users/{target.id}/deactivate",
        json={"reason": "Testing permissions"},
        headers=auth(student),
    )

    assert response.status_code == 403
    assert db.query(AuditEvent).count() == 0


def test_deactivated_user_token_is_revoked(client, db, admin):
    target = create_test_user(db, email="revoked@example.edu")

    old_token = create_auth_token(target)

    response = client.post(
        f"/api/v1/admin/users/{target.id}/deactivate",
        json={"reason": "Policy violation"},
        headers=auth(admin),
    )
    assert response.status_code == 200

    protected_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {old_token}"},
    )
    assert protected_response.status_code == 401


def test_deactivation_requires_reason(client, db, admin):
    target = create_test_user(db, email="no-reason@example.edu")

    response = client.post(
        f"/api/v1/admin/users/{target.id}/deactivate",
        json={"reason": "   "},
        headers=auth(admin),
    )

    assert response.status_code == 422
    assert db.query(AuditEvent).count() == 0


def test_admin_can_hide_listing(client, db, admin):
    from app.models import Book

    owner = create_test_user(db, email="listing-owner@example.edu")

    book = Book(
        isbn="9780132350884",
        title="Clean Code",
        author="Robert C. Martin",
    )
    db.add(book)
    db.flush()

    listing = Listing(
        owner_id=owner.id,
        book_id=book.id,
        condition_rank=3,
        location="Campus",
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)

    response = client.post(
        f"/api/v1/admin/listings/{listing.id}/hide",
        json={"reason": "Inappropriate listing content"},
        headers=auth(admin),
    )

    assert response.status_code == 200

    db.refresh(listing)
    assert listing.deleted_at is not None

    audit = db.query(AuditEvent).one()
    assert audit.actor_id == admin.id
    assert audit.target == f"LISTING:{listing.id}"
    assert audit.action == "LISTING_HIDDEN"
    assert audit.reason == "Inappropriate listing content"


def test_student_cannot_hide_listing(client, db):
    student = create_test_user(db, email="listing-student@example.edu")
    owner = create_test_user(db, email="listing-owner2@example.edu")

    from app.models import Book

    book = Book(isbn="9780132350885", title="Refactoring", author="Martin Fowler")
    db.add(book)
    db.flush()

    listing = Listing(
        owner_id=owner.id,
        book_id=book.id,
        condition_rank=3,
        location="Campus",
    )
    db.add(listing)
    db.commit()

    response = client.post(
        f"/api/v1/admin/listings/{listing.id}/hide",
        json={"reason": "Testing permissions"},
        headers=auth(student),
    )

    assert response.status_code == 403
    assert db.query(AuditEvent).count() == 0


@pytest.mark.parametrize("state", ["ACCEPTED", "ON_LOAN"])
def test_cannot_hide_listing_with_active_exchange(client, db, state):
    from app.models import Book, BorrowRequest, Match

    admin_user = User(
        name="Test Admin",
        email=f"admin-{state.lower()}@example.edu",
        password_hash="hashed_pw_test",
        role="admin",
        location="Campus Center",
    )
    db.add(admin_user)
    db.flush()

    lender = create_test_user(db, email=f"lender-{state.lower()}@example.edu")
    borrower = create_test_user(db, email=f"borrower-{state.lower()}@example.edu")

    book = Book(
        isbn=f"97801323508{88 if state == 'ACCEPTED' else 89}",
        title="Test Exchange Book",
        author="Test Author",
    )
    db.add(book)
    db.flush()

    listing = Listing(
        owner_id=lender.id,
        book_id=book.id,
        condition_rank=3,
        location="Campus",
        status="ON_LOAN" if state == "ON_LOAN" else "RESERVED",
    )
    request = BorrowRequest(
        borrower_id=borrower.id,
        isbn=book.isbn,
        location="Campus",
        status="FULFILLED",
    )
    db.add_all([listing, request])
    db.flush()

    match = Match(
        request_id=request.id,
        listing_id=listing.id,
        score=90,
        borrower_accepted=True,
        lender_accepted=True,
        status="ACCEPTED",
    )
    db.add(match)
    db.flush()

    exchange = Exchange(
        match_id=match.id,
        request_id=request.id,
        listing_id=listing.id,
        state=state,
    )
    db.add(exchange)
    db.commit()

    response = client.post(
        f"/api/v1/admin/listings/{listing.id}/hide",
        json={"reason": "Testing active exchange protection"},
        headers=auth(admin_user),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "LISTING_HAS_ACTIVE_EXCHANGE"

    db.refresh(listing)
    assert listing.deleted_at is None
    assert db.query(AuditEvent).count() == 0


def test_admin_can_view_audit_log(client, db, admin):
    db.add(
        AuditEvent(
            actor_id=admin.id,
            target="USER:101",
            action="USER_DEACTIVATED",
            reason="Policy violation",
        )
    )
    db.commit()

    response = client.get("/api/v1/admin/audit", headers=auth(admin))

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["actor_id"] == admin.id
    assert data["items"][0]["target"] == "USER:101"


def test_student_cannot_view_audit_log(client, db):
    student = create_test_user(db, email="audit-student@example.edu")

    response = client.get("/api/v1/admin/audit", headers=auth(student))

    assert response.status_code == 403


def test_anonymous_cannot_view_audit_log(client):
    response = client.get("/api/v1/admin/audit")

    assert response.status_code in (401, 403)


def test_audit_response_exposes_only_allowed_fields(client, db, admin):
    db.add(
        AuditEvent(
            actor_id=admin.id,
            target="LISTING:101",
            action="LISTING_HIDDEN",
            reason="Policy violation",
        )
    )
    db.commit()

    response = client.get("/api/v1/admin/audit", headers=auth(admin))

    assert response.status_code == 200
    item = response.json()["items"][0]

    assert set(item.keys()) == {"id", "actor_id", "target", "action", "timestamp", "reason"}
    assert not any(
        field in item for field in ("password", "password_hash", "token", "token_version")
    )


def test_audit_log_pagination_and_newest_first(client, db, admin):
    now = datetime.now(UTC)

    for i in range(3):
        db.add(
            AuditEvent(
                actor_id=admin.id,
                target=f"USER:{i}",
                action="USER_DEACTIVATED",
                reason=f"Reason {i}",
                timestamp=now + timedelta(minutes=i),
            )
        )

    db.commit()

    url = "/api/v1/admin/audit"
    headers = auth(admin)

    page1 = client.get(url, params={"page": 1, "page_size": 2}, headers=headers)
    page2 = client.get(url, params={"page": 2, "page_size": 2}, headers=headers)

    assert page1.status_code == 200
    assert page2.status_code == 200

    data1 = page1.json()
    data2 = page2.json()

    assert len(data1["items"]) == 2
    assert len(data2["items"]) == 1
    assert data1["total"] == 3
    assert data1["items"][0]["target"] == "USER:2"
    assert data1["items"][1]["target"] == "USER:1"
    assert data2["items"][0]["target"] == "USER:0"
