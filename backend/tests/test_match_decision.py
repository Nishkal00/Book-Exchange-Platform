"""Unit and security tests for Match Decision and Contact Privacy.

Covers:
- F-024: Participant accept/decline decisions, mutual acceptance, and exchange creation.
- SR-007 / TC-SEC-07: Contact disclosure isolation, authorization, and cancellation revocation.
- TC-MAT-04: Single accept, mutual accept, repeat decisions, conflicts, stale match.
"""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.main import app
from app.models import Book, BorrowRequest, Exchange, Listing, Match, Notification, User


def create_user(
    db: Session,
    email: str,
    name: str = "Test Student",
    role: str = "student",
    location: str = "Campus Center",
    department: str | None = "Computer Science",
    active: bool = True,
) -> User:
    """Helper to create and commit a user with department and contact info."""
    user = User(
        name=name,
        email=email.lower(),
        password_hash="test_password_hash_xyz",
        role=role,
        location=location,
        department=department,
        active=active,
        token_version=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_auth_token(user: User) -> str:
    """Helper to generate a valid JWT bearer token for the user."""
    settings = get_settings()
    expires_at = datetime.now(UTC) + timedelta(minutes=30)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "ver": user.token_version,
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def create_book_and_listing(
    db: Session,
    owner: User,
    title: str = "Algorithms Unlocked",
    author: str = "Thomas Cormen",
    isbn: str = "9780262518802",
    condition_rank: int = 4,
    location: str = "Campus Center",
    status: str = "AVAILABLE",
) -> Listing:
    """Helper to create a book and listing."""
    clean_isbn = isbn.replace("-", "").strip()
    book = db.query(Book).filter(Book.isbn == clean_isbn).first()
    if not book:
        book = Book(isbn=clean_isbn, title=title, author=author)
        db.add(book)
        db.flush()

    listing = Listing(
        owner_id=owner.id,
        book_id=book.id,
        condition_rank=condition_rank,
        location=location,
        status=status,
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


def create_borrow_request(
    db: Session,
    borrower: User,
    isbn: str = "9780262518802",
    query: str | None = None,
    location: str = "Campus Center",
    status: str = "OPEN",
) -> BorrowRequest:
    """Helper to create a borrow request."""
    clean_isbn = isbn.replace("-", "").strip() if isbn else None
    req = BorrowRequest(
        borrower_id=borrower.id,
        isbn=clean_isbn,
        query=query,
        location=location,
        status=status,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


def create_proposed_match(
    db: Session,
    request: BorrowRequest,
    listing: Listing,
    score: float = 95.0,
    relevance: float = 1.0,
    borrower_accepted: bool = False,
    lender_accepted: bool = False,
    status: str = "PROPOSED",
    expires_at: datetime | None = None,
) -> Match:
    """Helper to create a Match record."""
    match = Match(
        request_id=request.id,
        listing_id=listing.id,
        score=score,
        relevance=relevance,
        borrower_accepted=borrower_accepted,
        lender_accepted=lender_accepted,
        status=status,
        expires_at=expires_at,
    )
    db.add(match)
    db.commit()
    db.refresh(match)
    return match


@pytest.fixture
def client(db: Session) -> Generator[TestClient, None, None]:
    """TestClient fixture with dependency override for get_db."""
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ==============================================================================
# TC-MAT-04: Match Decision & Mutual Acceptance Lifecycle (F-024)
# ==============================================================================


def test_tc_mat_04_single_accept_does_not_create_exchange_or_disclose_contact(
    client: TestClient, db: Session
):
    """F-024 / TC-MAT-04: One participant accepts: no exchange/contact yet."""
    borrower = create_user(db, "borrower1@stu.pes.edu", name="Borrower One")
    lender = create_user(db, "lender1@stu.pes.edu", name="Lender One")
    listing = create_book_and_listing(db, lender, title="Operating Systems")
    req = create_borrow_request(db, borrower, isbn=listing.book.isbn)
    match = create_proposed_match(db, req, listing)

    borrower_token = create_auth_token(borrower)
    headers = {"Authorization": f"Bearer {borrower_token}"}

    # Borrower accepts
    response = client.post(
        f"/api/v1/matches/{match.id}/decision",
        json={"decision": "accept"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "PROPOSED"
    assert data["borrowerAccepted"] is True
    assert data["lenderAccepted"] is False
    assert data["exchangeId"] is None

    # Assert database state: listing still AVAILABLE, no Exchange created
    db.refresh(match)
    assert match.status == "PROPOSED"
    assert match.borrower_accepted is True
    assert match.lender_accepted is False

    db.refresh(listing)
    assert listing.status == "AVAILABLE"

    exchange_count = db.query(Exchange).count()
    assert exchange_count == 0

    # Partner notification created for lender
    notification = (
        db.query(Notification)
        .filter(
            Notification.user_id == lender.id,
            Notification.event_key == f"match:{match.id}:decision:{borrower.id}:accept",
        )
        .first()
    )
    assert notification is not None
    assert notification.event_type == "PARTNER_DECISION"

    # Contact cannot be accessed because no exchange exists
    contact_resp = client.get("/api/v1/exchanges/1/contact", headers=headers)
    assert contact_resp.status_code == 404


def test_tc_mat_04_mutual_acceptance_creates_single_exchange_and_reserves_listing(
    client: TestClient, db: Session
):
    """F-024 / TC-MAT-04: Both accept -> exchange created, listing RESERVED, request FULFILLED."""
    borrower = create_user(db, "borrower2@stu.pes.edu", name="Borrower Two")
    lender = create_user(db, "lender2@stu.pes.edu", name="Lender Two")
    listing = create_book_and_listing(db, lender, title="Database Systems")
    req = create_borrow_request(db, borrower, isbn=listing.book.isbn)
    match = create_proposed_match(db, req, listing)

    borrower_headers = {"Authorization": f"Bearer {create_auth_token(borrower)}"}
    lender_headers = {"Authorization": f"Bearer {create_auth_token(lender)}"}

    # Borrower accepts first
    r1 = client.post(
        f"/api/v1/matches/{match.id}/decision",
        json={"decision": "accept"},
        headers=borrower_headers,
    )
    assert r1.status_code == 200
    assert r1.json()["exchangeId"] is None

    # Lender accepts second -> triggers mutual acceptance
    r2 = client.post(
        f"/api/v1/matches/{match.id}/decision",
        json={"decision": "accept"},
        headers=lender_headers,
    )
    assert r2.status_code == 200
    data = r2.json()
    assert data["status"] == "ACCEPTED"
    assert data["borrowerAccepted"] is True
    assert data["lenderAccepted"] is True
    exchange_id = data["exchangeId"]
    assert exchange_id is not None

    # Exactly 1 exchange row in DB
    exchanges = db.query(Exchange).all()
    assert len(exchanges) == 1
    ex = exchanges[0]
    assert ex.id == exchange_id
    assert ex.state == "ACCEPTED"
    assert ex.listing_id == listing.id
    assert ex.request_id == req.id
    assert ex.match_id == match.id

    # Listing is RESERVED and Request is FULFILLED
    db.refresh(listing)
    db.refresh(req)
    db.refresh(match)
    assert listing.status == "RESERVED"
    assert req.status == "FULFILLED"
    assert match.status == "ACCEPTED"

    # Both participants receive exchange accepted notification
    notifications = (
        db.query(Notification)
        .filter(Notification.event_key == f"exchange:{exchange_id}:state:ACCEPTED")
        .all()
    )
    assert len(notifications) == 2
    assert {n.user_id for n in notifications} == {borrower.id, lender.id}


def test_tc_mat_04_repeat_decision_is_safe_and_idempotent(client: TestClient, db: Session):
    """F-024 / TC-MAT-04: Repeat decision is safe (idempotent) before and after mutual accept."""
    borrower = create_user(db, "repeat_b@stu.pes.edu", name="Repeat Borrower")
    lender = create_user(db, "repeat_l@stu.pes.edu", name="Repeat Lender")
    listing = create_book_and_listing(db, lender, title="Computer Networks")
    req = create_borrow_request(db, borrower, isbn=listing.book.isbn)
    match = create_proposed_match(db, req, listing)

    borrower_headers = {"Authorization": f"Bearer {create_auth_token(borrower)}"}
    lender_headers = {"Authorization": f"Bearer {create_auth_token(lender)}"}

    # Borrower accepts once
    r1 = client.post(
        f"/api/v1/matches/{match.id}/decision",
        json={"decision": "accept"},
        headers=borrower_headers,
    )
    assert r1.status_code == 200

    # Borrower accepts a second time while waiting for partner
    r1_repeat = client.post(
        f"/api/v1/matches/{match.id}/decision",
        json={"decision": "accept"},
        headers=borrower_headers,
    )
    assert r1_repeat.status_code == 200
    assert r1_repeat.json()["status"] == "PROPOSED"
    assert r1_repeat.json()["borrowerAccepted"] is True
    assert r1_repeat.json()["exchangeId"] is None
    assert db.query(Exchange).count() == 0

    # Lender accepts -> mutual acceptance
    r2 = client.post(
        f"/api/v1/matches/{match.id}/decision",
        json={"decision": "accept"},
        headers=lender_headers,
    )
    assert r2.status_code == 200
    exchange_id = r2.json()["exchangeId"]
    assert exchange_id is not None

    # Borrower calls accept again AFTER mutual acceptance
    r_b_post = client.post(
        f"/api/v1/matches/{match.id}/decision",
        json={"decision": "accept"},
        headers=borrower_headers,
    )
    assert r_b_post.status_code == 200
    assert r_b_post.json()["status"] == "ACCEPTED"
    assert r_b_post.json()["exchangeId"] == exchange_id

    # Lender calls accept again AFTER mutual acceptance
    r_l_post = client.post(
        f"/api/v1/matches/{match.id}/decision",
        json={"decision": "accept"},
        headers=lender_headers,
    )
    assert r_l_post.status_code == 200
    assert r_l_post.json()["status"] == "ACCEPTED"
    assert r_l_post.json()["exchangeId"] == exchange_id

    # Ensure still exactly 1 exchange
    assert db.query(Exchange).count() == 1


def test_tc_mat_04_unrelated_user_decision_rejected_with_403(client: TestClient, db: Session):
    """F-024 / TC-MAT-04: Non-participant receives 403 Forbidden."""
    borrower = create_user(db, "match_b@stu.pes.edu")
    lender = create_user(db, "match_l@stu.pes.edu")
    unrelated = create_user(db, "unrelated_student@stu.pes.edu")
    listing = create_book_and_listing(db, lender)
    req = create_borrow_request(db, borrower, isbn=listing.book.isbn)
    match = create_proposed_match(db, req, listing)

    unrelated_headers = {"Authorization": f"Bearer {create_auth_token(unrelated)}"}

    res = client.post(
        f"/api/v1/matches/{match.id}/decision",
        json={"decision": "accept"},
        headers=unrelated_headers,
    )
    assert res.status_code == 403
    assert "Not a participant" in res.json()["detail"]


def test_tc_mat_04_stale_match_cannot_be_accepted_returns_409(client: TestClient, db: Session):
    """F-024 / TC-MAT-04: Stale match (DECLINED or EXPIRED) returns 409 STALE_MATCH."""
    borrower = create_user(db, "stale_b@stu.pes.edu")
    lender = create_user(db, "stale_l@stu.pes.edu")
    listing = create_book_and_listing(db, lender)
    req = create_borrow_request(db, borrower, isbn=listing.book.isbn)

    # 1. Match in DECLINED state
    declined_match = create_proposed_match(db, req, listing, status="DECLINED")
    headers = {"Authorization": f"Bearer {create_auth_token(borrower)}"}

    res1 = client.post(
        f"/api/v1/matches/{declined_match.id}/decision",
        json={"decision": "accept"},
        headers=headers,
    )
    assert res1.status_code == 409
    assert res1.json()["detail"] == "STALE_MATCH"

    # 2. Match in EXPIRED state
    expired_match = create_proposed_match(db, req, listing, status="EXPIRED")
    res2 = client.post(
        f"/api/v1/matches/{expired_match.id}/decision",
        json={"decision": "accept"},
        headers=headers,
    )
    assert res2.status_code == 409
    assert res2.json()["detail"] == "STALE_MATCH"

    # 3. Match with past expires_at
    past_time = datetime.now(UTC) - timedelta(hours=1)
    past_match = create_proposed_match(db, req, listing, status="PROPOSED", expires_at=past_time)
    res3 = client.post(
        f"/api/v1/matches/{past_match.id}/decision",
        json={"decision": "accept"},
        headers=headers,
    )
    assert res3.status_code == 409
    assert res3.json()["detail"] == "STALE_MATCH"


def test_tc_mat_04_competing_decisions_cannot_create_second_active_exchange(
    client: TestClient, db: Session
):
    """F-024 / TC-MAT-04: Conflicting decisions cannot create a second active exchange (409)."""
    borrower1 = create_user(db, "b1@stu.pes.edu")
    borrower2 = create_user(db, "b2@stu.pes.edu")
    lender = create_user(db, "shared_lender@stu.pes.edu")

    listing = create_book_and_listing(db, lender, title="Single Shared Book")
    req1 = create_borrow_request(db, borrower1, isbn=listing.book.isbn)
    req2 = create_borrow_request(db, borrower2, isbn=listing.book.isbn)

    m1 = create_proposed_match(db, req1, listing)
    m2 = create_proposed_match(db, req2, listing)

    b1_headers = {"Authorization": f"Bearer {create_auth_token(borrower1)}"}
    b2_headers = {"Authorization": f"Bearer {create_auth_token(borrower2)}"}
    lender_headers = {"Authorization": f"Bearer {create_auth_token(lender)}"}

    # Borrower 1 accepts and lender accepts -> M1 creates active exchange
    client.post(
        f"/api/v1/matches/{m1.id}/decision", json={"decision": "accept"}, headers=b1_headers
    )
    res_m1 = client.post(
        f"/api/v1/matches/{m1.id}/decision", json={"decision": "accept"}, headers=lender_headers
    )
    assert res_m1.status_code == 200
    assert res_m1.json()["status"] == "ACCEPTED"

    # M2: Borrower 2 tries to accept the now RESERVED listing
    # M2 was automatically marked EXPIRED when M1 mutually accepted!
    db.refresh(m2)
    assert m2.status == "EXPIRED"

    res_m2 = client.post(
        f"/api/v1/matches/{m2.id}/decision",
        json={"decision": "accept"},
        headers=b2_headers,
    )
    assert res_m2.status_code == 409
    assert res_m2.json()["detail"] == "STALE_MATCH"

    # Only 1 exchange in DB
    assert db.query(Exchange).count() == 1


def test_tc_mat_04_decline_decision_and_validation(client: TestClient, db: Session):
    """F-024 / TC-MAT-04: Decline decision flow, partner notification, and input validation."""
    borrower = create_user(db, "dec_b@stu.pes.edu")
    lender = create_user(db, "dec_l@stu.pes.edu")
    listing = create_book_and_listing(db, lender)
    req = create_borrow_request(db, borrower, isbn=listing.book.isbn)
    match = create_proposed_match(db, req, listing)

    borrower_headers = {"Authorization": f"Bearer {create_auth_token(borrower)}"}

    # Invalid decision payload
    r_invalid = client.post(
        f"/api/v1/matches/{match.id}/decision",
        json={"decision": "undecided"},
        headers=borrower_headers,
    )
    assert r_invalid.status_code == 422

    # Borrower declines match
    r_dec = client.post(
        f"/api/v1/matches/{match.id}/decision",
        json={"decision": "decline"},
        headers=borrower_headers,
    )
    assert r_dec.status_code == 200
    assert r_dec.json()["status"] == "DECLINED"

    db.refresh(match)
    assert match.status == "DECLINED"

    # Repeating decline is idempotent
    r_dec_repeat = client.post(
        f"/api/v1/matches/{match.id}/decision",
        json={"decision": "decline"},
        headers=borrower_headers,
    )
    assert r_dec_repeat.status_code == 200
    assert r_dec_repeat.json()["status"] == "DECLINED"

    # Partner received notification
    notif = (
        db.query(Notification)
        .filter(
            Notification.user_id == lender.id,
            Notification.event_key == f"match:{match.id}:decision:{borrower.id}:decline",
        )
        .first()
    )
    assert notif is not None


# ==============================================================================
# TC-SEC-07: Contact Privacy & Access Control (SR-007 / F-024)
# ==============================================================================


def test_tc_sec_07_public_listings_and_match_views_omit_private_contact(
    client: TestClient, db: Session
):
    """SR-007 / TC-SEC-07: Public listings, search, and matches never disclose contact info."""
    owner = create_user(
        db,
        "private_owner@stu.pes.edu",
        name="Private Owner",
        department="Mechanical Engineering",
        location="Campus Center",
    )
    borrower = create_user(
        db,
        "private_borrower@stu.pes.edu",
        name="Private Borrower",
        department="Biotechnology",
        location="Campus Center",
    )
    listing = create_book_and_listing(db, owner, title="Secret Book of Algorithms")
    req = create_borrow_request(db, borrower, isbn=listing.book.isbn)

    # 1. Public listings endpoint
    res_list = client.get("/api/v1/listings")
    assert res_list.status_code == 200
    items = res_list.json()["items"]
    assert len(items) >= 1
    for item in items:
        assert "email" not in item
        assert "department" not in item
        assert "phone" not in item

    # 2. Match suggestions endpoint for borrower
    borrower_headers = {"Authorization": f"Bearer {create_auth_token(borrower)}"}
    res_matches = client.get(f"/api/v1/requests/{req.id}/matches", headers=borrower_headers)
    assert res_matches.status_code == 200
    match_list = res_matches.json()
    assert len(match_list) >= 1
    for m in match_list:
        listing_data = m["listing"]
        assert "email" not in listing_data
        assert "department" not in listing_data
        assert "phone" not in listing_data


def test_tc_sec_07_contact_disclosure_only_to_mutual_participants_of_active_exchange(
    client: TestClient, db: Session
):
    """SR-007 / TC-SEC-07: Contact disclosed ONLY after mutual accept, only to participants."""
    borrower = create_user(
        db,
        "bob_borrower@stu.pes.edu",
        name="Bob Borrower",
        department="Computer Science",
        location="Hostel Block A",
    )
    lender = create_user(
        db,
        "alice_lender@stu.pes.edu",
        name="Alice Lender",
        department="Electronics",
        location="Library",
    )
    unrelated = create_user(db, "eve_snooper@stu.pes.edu", name="Eve Snooper")

    listing = create_book_and_listing(db, lender, title="Digital Design")
    req = create_borrow_request(db, borrower, isbn=listing.book.isbn)
    match = create_proposed_match(db, req, listing)

    borrower_token = create_auth_token(borrower)
    lender_token = create_auth_token(lender)
    unrelated_token = create_auth_token(unrelated)

    borrower_headers = {"Authorization": f"Bearer {borrower_token}"}
    lender_headers = {"Authorization": f"Bearer {lender_token}"}
    unrelated_headers = {"Authorization": f"Bearer {unrelated_token}"}

    # Before mutual acceptance: contact endpoint returns 404
    pre_resp = client.get("/api/v1/exchanges/999/contact", headers=borrower_headers)
    assert pre_resp.status_code == 404

    # Mutual acceptance occurs
    client.post(
        f"/api/v1/matches/{match.id}/decision",
        json={"decision": "accept"},
        headers=borrower_headers,
    )
    res_accept = client.post(
        f"/api/v1/matches/{match.id}/decision", json={"decision": "accept"}, headers=lender_headers
    )
    exchange_id = res_accept.json()["exchangeId"]
    assert exchange_id is not None

    # Unauthenticated caller -> 401 Unauthorized
    unauth_resp = client.get(f"/api/v1/exchanges/{exchange_id}/contact")
    assert unauth_resp.status_code == 401

    # Unrelated user -> 403 Forbidden
    unrelated_resp = client.get(
        f"/api/v1/exchanges/{exchange_id}/contact", headers=unrelated_headers
    )
    assert unrelated_resp.status_code == 403
    assert "Not authorized" in unrelated_resp.json()["detail"]

    # Borrower requests contact -> receives lender's verified contact details
    borrower_view = client.get(f"/api/v1/exchanges/{exchange_id}/contact", headers=borrower_headers)
    assert borrower_view.status_code == 200
    b_data = borrower_view.json()
    assert b_data["userId"] == lender.id
    assert b_data["name"] == "Alice Lender"
    assert b_data["email"] == "alice_lender@stu.pes.edu"
    assert b_data["department"] == "Electronics"
    assert b_data["location"] == "Library"
    assert "password_hash" not in b_data

    # Lender requests contact -> receives borrower's verified contact details
    lender_view = client.get(f"/api/v1/exchanges/{exchange_id}/contact", headers=lender_headers)
    assert lender_view.status_code == 200
    l_data = lender_view.json()
    assert l_data["userId"] == borrower.id
    assert l_data["name"] == "Bob Borrower"
    assert l_data["email"] == "bob_borrower@stu.pes.edu"
    assert l_data["department"] == "Computer Science"
    assert l_data["location"] == "Hostel Block A"
    assert "password_hash" not in l_data


def test_tc_sec_07_cancellation_revokes_contact_access_and_restores_listing(
    client: TestClient, db: Session
):
    """SR-007 / TC-SEC-07: Cancellation revokes contact (403) and frees listing to AVAILABLE."""
    borrower = create_user(db, "canceller_b@stu.pes.edu", name="Canceller Borrower")
    lender = create_user(db, "canceller_l@stu.pes.edu", name="Canceller Lender")
    listing = create_book_and_listing(db, lender, title="Calculus Early Transcendentals")
    req = create_borrow_request(db, borrower, isbn=listing.book.isbn)
    match = create_proposed_match(db, req, listing)

    borrower_headers = {"Authorization": f"Bearer {create_auth_token(borrower)}"}
    lender_headers = {"Authorization": f"Bearer {create_auth_token(lender)}"}
    unrelated_headers = {
        "Authorization": f"Bearer {create_auth_token(create_user(db, 'other@stu.pes.edu'))}"
    }

    # Mutual acceptance
    client.post(
        f"/api/v1/matches/{match.id}/decision",
        json={"decision": "accept"},
        headers=borrower_headers,
    )
    res_accept = client.post(
        f"/api/v1/matches/{match.id}/decision", json={"decision": "accept"}, headers=lender_headers
    )
    exchange_id = res_accept.json()["exchangeId"]

    # Verify contact is accessible before cancellation
    c_pre = client.get(f"/api/v1/exchanges/{exchange_id}/contact", headers=borrower_headers)
    assert c_pre.status_code == 200

    # Unrelated user cannot cancel exchange
    r_unrelated_cancel = client.post(
        f"/api/v1/exchanges/{exchange_id}/cancel", headers=unrelated_headers
    )
    assert r_unrelated_cancel.status_code in (403, 404)

    # Borrower cancels the exchange before handover
    cancel_res = client.post(f"/api/v1/exchanges/{exchange_id}/cancel", headers=borrower_headers)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["state"] == "CANCELLED"
    assert cancel_res.json()["cancelledAt"] is not None

    # Listing status is restored to AVAILABLE
    db.refresh(listing)
    assert listing.status == "AVAILABLE"

    # Partner notification created
    notif = (
        db.query(Notification)
        .filter(
            Notification.user_id == lender.id,
            Notification.event_key == f"exchange:{exchange_id}:state:CANCELLED",
        )
        .first()
    )
    assert notif is not None
    assert notif.event_type == "EXCHANGE_UPDATED"

    # Contact access is now revoked for BOTH borrower and lender (403 Forbidden)
    c_b_post = client.get(f"/api/v1/exchanges/{exchange_id}/contact", headers=borrower_headers)
    assert c_b_post.status_code == 403
    assert "revoked" in c_b_post.json()["detail"].lower()

    c_l_post = client.get(f"/api/v1/exchanges/{exchange_id}/contact", headers=lender_headers)
    assert c_l_post.status_code == 403
    assert "revoked" in c_l_post.json()["detail"].lower()


def test_tc_sec_07_exchange_history_omits_private_contact_details(client: TestClient, db: Session):
    """SR-007: GET /api/v1/exchanges lists participant history without disclosing emails."""
    borrower = create_user(db, "hist_b@stu.pes.edu", name="History Borrower")
    lender = create_user(db, "hist_l@stu.pes.edu", name="History Lender")
    listing = create_book_and_listing(db, lender, title="Discrete Mathematics")
    req = create_borrow_request(db, borrower, isbn=listing.book.isbn)
    match = create_proposed_match(db, req, listing)

    borrower_headers = {"Authorization": f"Bearer {create_auth_token(borrower)}"}
    lender_headers = {"Authorization": f"Bearer {create_auth_token(lender)}"}

    # Mutually accept
    client.post(
        f"/api/v1/matches/{match.id}/decision",
        json={"decision": "accept"},
        headers=borrower_headers,
    )
    client.post(
        f"/api/v1/matches/{match.id}/decision", json={"decision": "accept"}, headers=lender_headers
    )

    # Borrower queries paginated history
    b_hist = client.get(
        "/api/v1/exchanges?limit=20&offset=0",
        headers=borrower_headers,
    )
    assert b_hist.status_code == 200
    borrower_body = b_hist.json()

    assert borrower_body["total"] == 1
    assert borrower_body["limit"] == 20
    assert borrower_body["offset"] == 0
    assert len(borrower_body["items"]) == 1

    item = borrower_body["items"][0]
    assert item["role"] == "borrower"
    assert item["partnerId"] == lender.id
    assert item["partnerName"] == lender.name
    assert item["bookTitle"] == "Discrete Mathematics"
    assert "email" not in item
    assert "department" not in item
    assert "password_hash" not in item

    # Lender queries paginated history
    l_hist = client.get(
        "/api/v1/exchanges?limit=20&offset=0",
        headers=lender_headers,
    )
    assert l_hist.status_code == 200
    lender_body = l_hist.json()

    assert lender_body["total"] == 1
    assert lender_body["limit"] == 20
    assert lender_body["offset"] == 0
    assert len(lender_body["items"]) == 1

    l_item = lender_body["items"][0]
    assert l_item["role"] == "lender"
    assert l_item["partnerId"] == borrower.id
    assert l_item["partnerName"] == borrower.name
    assert "email" not in l_item
    assert "department" not in l_item
    assert "password_hash" not in l_item
