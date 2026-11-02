"""Tests for Matching Engine, Scoring, Locking, and Re-match (F-022).

Covers TC-MAT-01, TC-MAT-02, TC-MAT-03.
"""

from __future__ import annotations

import concurrent.futures
import os
import tempfile
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.database import Base, get_db
from app.main import app
from app.models import Book, BorrowRequest, Exchange, Listing, Match, Notification, User
from app.services.matching import (
    calculate_match_score,
    calculate_trigram_similarity,
    handle_match_decision,
    recompute_matches_for_request,
)


def create_user(
    db: Session,
    email: str,
    name: str = "Test Student",
    role: str = "student",
    location: str = "Campus Center",
    active: bool = True,
) -> User:
    """Helper to create and commit a user."""
    user = User(
        name=name,
        email=email.lower(),
        password_hash="test_hash_for_matching",
        role=role,
        location=location,
        active=active,
        token_version=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_token(user: User) -> str:
    """Helper to create a valid JWT for an authenticated user."""
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
    title: str,
    author: str,
    isbn: str,
    condition_rank: int,
    location: str,
    status: str = "AVAILABLE",
    deleted_at: datetime | None = None,
    created_at: datetime | None = None,
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
        deleted_at=deleted_at,
    )
    if created_at is not None:
        listing.created_at = created_at
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


@pytest.fixture
def client(db: Session):
    """TestClient fixture with overridden get_db dependency."""

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ==============================================================================
# Unit Tests for Matching Engine Core Logic
# ==============================================================================


def test_trigram_similarity_cases():
    """Verify trigram similarity calculation matches pg_trgm behavior."""
    assert calculate_trigram_similarity("", "") == 0.0
    assert calculate_trigram_similarity("Database", "") == 0.0
    assert calculate_trigram_similarity("Database Systems", "Database Systems") == 1.0
    assert calculate_trigram_similarity("Database Systems", "Cooking Recipes") == 0.0

    sim_partial = calculate_trigram_similarity(
        "Database Systems", "Introduction to Database Systems"
    )
    assert 0.3 <= sim_partial <= 1.0


def test_calculate_match_score_formula():
    """Verify Score = 70*relevance + 20*same_location + 10*(condition_rank/4)."""
    # 1. Exact ISBN, same location, condition NEW (4)
    res = calculate_match_score(
        request_isbn="9780132143011",
        request_query=None,
        request_location="Campus Center",
        listing_isbn="978-0-13-214301-1",
        listing_title="Distributed Systems",
        listing_author="Coulouris",
        listing_condition_rank=4,
        listing_location="Campus Center",
    )
    assert res is not None
    score, relevance = res
    # 70*1.0 + 20*1.0 + 10*(4/4) = 100.0
    assert score == 100.0
    assert relevance == 1.0

    # 2. Exact ISBN, different location, condition GOOD (3)
    res2 = calculate_match_score(
        request_isbn="9780132143011",
        request_query=None,
        request_location="Campus Center",
        listing_isbn="9780132143011",
        listing_title="Distributed Systems",
        listing_author="Coulouris",
        listing_condition_rank=3,
        listing_location="Hostel Block A",
    )
    assert res2 is not None
    score2, relevance2 = res2
    # 70*1.0 + 20*0.0 + 10*(3/4) = 77.5
    assert score2 == 77.5
    assert relevance2 == 1.0

    # 3. Mismatched ISBN -> None
    res3 = calculate_match_score(
        request_isbn="9780132143011",
        request_query=None,
        request_location="Campus Center",
        listing_isbn="9780131103627",
        listing_title="C Programming",
        listing_author="Kernighan",
        listing_condition_rank=4,
        listing_location="Campus Center",
    )
    assert res3 is None


# ==============================================================================
# TC-MAT-01: Fixed candidate fixtures, exact score order, top-five cap, exclusions (F-022)
# ==============================================================================


def test_tc_mat_01_fixed_candidate_fixtures_and_exclusions(client: TestClient, db: Session):
    """TC-MAT-01: Use fixed candidate fixtures with known relevance/location/condition scores.

    Assert exact score order and top-five cap; exclude own/deleted/inactive offers.
    """
    # 1. Create borrower and target ISBN
    borrower = create_user(db, email="borrower_tc_mat_01@stu.pes.edu", location="Campus Center")
    borrower_token = create_token(borrower)
    borrower_headers = {"Authorization": f"Bearer {borrower_token}"}
    target_isbn = "9780132143011"

    # Create distinct lenders
    lenders = [
        create_user(db, email=f"lender_{i}_tc_mat_01@stu.pes.edu", location="Lab 3")
        for i in range(1, 10)
    ]

    # Create 6 valid candidates for target ISBN with KNOWN scores:
    # Cand 1: Same loc ("Campus Center"), Condition 4 (NEW)  -> 70*1 + 20*1 + 10*(4/4) = 100.0
    c1 = create_book_and_listing(
        db,
        owner=lenders[0],
        title="Distributed Systems",
        author="Coulouris",
        isbn=target_isbn,
        condition_rank=4,
        location="Campus Center",
    )
    # Cand 2: Same loc ("Campus Center"), Condition 3 (GOOD) -> 70*1 + 20*1 + 10*(3/4) = 97.5
    c2 = create_book_and_listing(
        db,
        owner=lenders[1],
        title="Distributed Systems",
        author="Coulouris",
        isbn=target_isbn,
        condition_rank=3,
        location="Campus Center",
    )
    # Cand 3: Diff loc ("Lab 3"), Condition 4 (NEW)          -> 70*1 + 20*0 + 10*(4/4) = 80.0
    c3 = create_book_and_listing(
        db,
        owner=lenders[2],
        title="Distributed Systems",
        author="Coulouris",
        isbn=target_isbn,
        condition_rank=4,
        location="Lab 3",
    )
    # Cand 4: Diff loc ("Lab 3"), Condition 3 (GOOD)         -> 70*1 + 20*0 + 10*(3/4) = 77.5
    c4 = create_book_and_listing(
        db,
        owner=lenders[3],
        title="Distributed Systems",
        author="Coulouris",
        isbn=target_isbn,
        condition_rank=3,
        location="Lab 3",
    )
    # Cand 5: Diff loc ("Lab 3"), Condition 2 (FAIR)         -> 70*1 + 20*0 + 10*(2/4) = 75.0
    c5 = create_book_and_listing(
        db,
        owner=lenders[4],
        title="Distributed Systems",
        author="Coulouris",
        isbn=target_isbn,
        condition_rank=2,
        location="Lab 3",
    )
    # Cand 6: Diff loc ("Lab 3"), Condition 1 (POOR)         -> 70*1 + 20*0 + 10*(1/4) = 72.5
    c6 = create_book_and_listing(
        db,
        owner=lenders[5],
        title="Distributed Systems",
        author="Coulouris",
        isbn=target_isbn,
        condition_rank=1,
        location="Lab 3",
    )

    # Exclusions to verify:
    # - Borrower's own listing
    own_listing = create_book_and_listing(
        db,
        owner=borrower,
        title="Distributed Systems",
        author="Coulouris",
        isbn=target_isbn,
        condition_rank=4,
        location="Campus Center",
    )
    # - Deleted listing
    deleted_listing = create_book_and_listing(
        db,
        owner=lenders[6],
        title="Distributed Systems",
        author="Coulouris",
        isbn=target_isbn,
        condition_rank=4,
        location="Campus Center",
        deleted_at=datetime.now(UTC),
    )
    # - Inactive owner's listing
    inactive_user = create_user(
        db, email="inactive_owner_tc_mat_01@stu.pes.edu", location="Campus Center", active=False
    )
    inactive_listing = create_book_and_listing(
        db,
        owner=inactive_user,
        title="Distributed Systems",
        author="Coulouris",
        isbn=target_isbn,
        condition_rank=4,
        location="Campus Center",
    )
    # - Unavailable listing
    unavailable_listing = create_book_and_listing(
        db,
        owner=lenders[7],
        title="Distributed Systems",
        author="Coulouris",
        isbn=target_isbn,
        condition_rank=4,
        location="Campus Center",
        status="UNAVAILABLE",
    )

    # 2. Borrower creates borrow request for target ISBN
    res_req = client.post(
        "/api/v1/requests",
        json={"isbn": target_isbn, "location": "Campus Center"},
        headers=borrower_headers,
    )
    assert res_req.status_code == 201
    req_id = res_req.json()["id"]

    # 3. Fetch matches
    res_matches = client.get(
        f"/api/v1/requests/{req_id}/matches",
        headers=borrower_headers,
    )
    assert res_matches.status_code == 200
    suggestions = res_matches.json()

    # 4. Assert Top-Five Cap: exactly 5 items returned (cand 6 capped out)
    assert len(suggestions) == 5

    # 5. Assert exact score order and values
    scores = [s["score"] for s in suggestions]
    assert scores == [100.0, 97.5, 80.0, 77.5, 75.0]

    returned_listing_ids = [s["listing"]["id"] for s in suggestions]
    assert returned_listing_ids == [c1.id, c2.id, c3.id, c4.id, c5.id]
    assert c6.id not in returned_listing_ids

    # 6. Assert exclusions: own, deleted, inactive, unavailable NEVER appear
    assert own_listing.id not in returned_listing_ids
    assert deleted_listing.id not in returned_listing_ids
    assert inactive_listing.id not in returned_listing_ids
    assert unavailable_listing.id not in returned_listing_ids

    # 7. Assert contact privacy (SR-007): responses MUST omit email and private fields
    for s in suggestions:
        assert "email" not in s["listing"]
        assert "password_hash" not in s["listing"]
        assert "token_version" not in s["listing"]


# ==============================================================================
# TC-MAT-02: Simultaneous mutual acceptances competing for one listing (F-022)
# ==============================================================================


def test_tc_mat_02_simultaneous_mutual_acceptances(client: TestClient):
    """TC-MAT-02: Run two simultaneous mutual acceptances competing for one listing

    using separate DB connections. Exactly one active exchange; loser -> 409;
    no duplicate reservation.
    """
    # Create isolated file database with WAL mode so separate threads have independent connections
    db_file = os.path.join(
        tempfile.gettempdir(), f"tc_mat_02_{int(datetime.now(UTC).timestamp())}.db"
    )
    if os.path.exists(db_file):
        os.remove(db_file)

    isolated_engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"timeout": 15},
    )

    @event.listens_for(isolated_engine, "connect")
    def _fk_on(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")
        dbapi_conn.execute("PRAGMA journal_mode=WAL")

    Base.metadata.create_all(isolated_engine)
    SessionLocal = sessionmaker(bind=isolated_engine)

    try:
        # Setup seed data with session 1
        with SessionLocal() as init_db:
            lender = create_user(
                init_db, email="lender_tc_mat_02@stu.pes.edu", location="Campus Center"
            )
            b1 = create_user(
                init_db, email="borrower1_tc_mat_02@stu.pes.edu", location="Campus Center"
            )
            b2 = create_user(
                init_db, email="borrower2_tc_mat_02@stu.pes.edu", location="Campus Center"
            )

            listing = create_book_and_listing(
                init_db,
                owner=lender,
                title="Database System Concepts",
                author="Silberschatz",
                isbn="9780073523323",
                condition_rank=4,
                location="Campus Center",
            )

            r1 = BorrowRequest(
                borrower_id=b1.id, isbn="9780073523323", location="Campus Center", status="OPEN"
            )
            r2 = BorrowRequest(
                borrower_id=b2.id, isbn="9780073523323", location="Campus Center", status="OPEN"
            )
            init_db.add_all([r1, r2])
            init_db.commit()

            # Both match the same listing
            m1 = Match(
                request_id=r1.id,
                listing_id=listing.id,
                score=100.0,
                relevance=1.0,
                status="PROPOSED",
            )
            m2 = Match(
                request_id=r2.id,
                listing_id=listing.id,
                score=100.0,
                relevance=1.0,
                status="PROPOSED",
            )
            init_db.add_all([m1, m2])
            init_db.commit()

            # Pre-accept by each borrower
            m1.borrower_accepted = True
            m2.borrower_accepted = True
            init_db.commit()

            lender_id = lender.id
            m1_id = m1.id
            m2_id = m2.id
            listing_id = listing.id

        # Function executed by competing lender threads on separate DB sessions
        def lender_accept_match(match_id: int) -> int:
            from app.services.matching import handle_match_decision

            with SessionLocal() as worker_db:
                try:
                    handle_match_decision(
                        db=worker_db,
                        match_id=match_id,
                        current_user_id=lender_id,
                        decision="accept",
                    )
                    return 200
                except HTTPException as ex:
                    return ex.status_code
                except Exception:
                    return 500

        # Run two simultaneous acceptances competing for the exact same listing
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(lender_accept_match, m1_id)
            f2 = executor.submit(lender_accept_match, m2_id)
            results = [f1.result(), f2.result()]

        # Assert exactly one winner (200) and one loser (409 Conflict)
        assert 200 in results
        assert 409 in results
        assert results.count(200) == 1
        assert results.count(409) == 1

        # Verify database state with fresh session
        with SessionLocal() as verify_db:
            lst = verify_db.query(Listing).filter(Listing.id == listing_id).one()
            assert lst.status == "RESERVED"

            active_exchanges = (
                verify_db.query(Exchange)
                .filter(
                    Exchange.listing_id == listing_id,
                    Exchange.state.in_(["ACCEPTED", "ON_LOAN"]),
                )
                .all()
            )
            # Exactly one active exchange created; never reserve one listing for two exchanges!
            assert len(active_exchanges) == 1
    finally:
        isolated_engine.dispose()
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
            except OSError:
                pass


# ==============================================================================
# TC-MAT-03: Decline/expire, listing status change, deterministic ties, empty state (F-022)
# ==============================================================================


def test_tc_mat_03_decline_expire_recompute_and_deterministic_ties(client: TestClient, db: Session):
    """TC-MAT-03: Decline or expire a suggestion, change listing status, then recompute.

    No stale/unavailable result; deterministic tie ordering and correct empty state.
    """
    borrower = create_user(db, email="borrower_tc_mat_03@stu.pes.edu", location="Campus Center")
    borrower_token = create_token(borrower)
    borrower_headers = {"Authorization": f"Bearer {borrower_token}"}
    target_isbn = "9780262033848"

    lender1 = create_user(db, email="lender1_tc_mat_03@stu.pes.edu", location="Campus Center")
    lender2 = create_user(db, email="lender2_tc_mat_03@stu.pes.edu", location="Campus Center")
    lender3 = create_user(db, email="lender3_tc_mat_03@stu.pes.edu", location="Lab 3")

    # 1. Deterministic Tie Ordering Verification
    # Two listings with IDENTICAL score (same location, condition 4, same ISBN)
    # Listing A created at t0, Listing B created at t0 + 1 hour (newer)
    t0 = datetime(2026, 11, 1, 10, 0, 0, tzinfo=UTC)
    t1 = datetime(2026, 11, 1, 11, 0, 0, tzinfo=UTC)

    l_older = create_book_and_listing(
        db,
        owner=lender1,
        title="Introduction to Algorithms",
        author="Cormen",
        isbn=target_isbn,
        condition_rank=4,
        location="Campus Center",
        created_at=t0,
    )
    l_newer = create_book_and_listing(
        db,
        owner=lender2,
        title="Introduction to Algorithms",
        author="Cormen",
        isbn=target_isbn,
        condition_rank=4,
        location="Campus Center",
        created_at=t1,
    )
    l_diff_loc = create_book_and_listing(
        db,
        owner=lender3,
        title="Introduction to Algorithms",
        author="Cormen",
        isbn=target_isbn,
        condition_rank=4,
        location="Lab 3",
    )

    res_req = client.post(
        "/api/v1/requests",
        json={"isbn": target_isbn, "location": "Campus Center"},
        headers=borrower_headers,
    )
    req_id = res_req.json()["id"]

    res_m1 = client.get(f"/api/v1/requests/{req_id}/matches", headers=borrower_headers)
    assert res_m1.status_code == 200
    items = res_m1.json()
    assert len(items) == 3

    # Newer listing must appear before older listing for deterministic tie-breaking
    assert items[0]["listing"]["id"] == l_newer.id
    assert items[1]["listing"]["id"] == l_older.id
    assert items[2]["listing"]["id"] == l_diff_loc.id

    # 2. Decline a suggestion and recompute
    # Borrower declines the top suggestion (l_newer)
    match_to_decline_id = items[0]["matchId"]
    res_dec = client.post(
        f"/api/v1/matches/{match_to_decline_id}/decision",
        json={"decision": "decline"},
        headers=borrower_headers,
    )
    assert res_dec.status_code == 200
    assert res_dec.json()["status"] == "DECLINED"

    # Re-fetch matches: declined match must NOT appear
    res_m2 = client.get(f"/api/v1/requests/{req_id}/matches", headers=borrower_headers)
    items_after_decline = res_m2.json()
    assert len(items_after_decline) == 2
    assert not any(it["listing"]["id"] == l_newer.id for it in items_after_decline)
    assert items_after_decline[0]["listing"]["id"] == l_older.id

    # 3. Change listing status and recompute
    # Lender of l_older marks it UNAVAILABLE
    l_older.status = "UNAVAILABLE"
    db.commit()

    # Re-fetch matches: l_older must NOT appear (no stale/unavailable results)
    res_m3 = client.get(f"/api/v1/requests/{req_id}/matches", headers=borrower_headers)
    items_after_status_change = res_m3.json()
    assert len(items_after_status_change) == 1
    assert items_after_status_change[0]["listing"]["id"] == l_diff_loc.id

    # Soft-delete l_diff_loc -> empty state
    l_diff_loc.deleted_at = datetime.now(UTC)
    db.commit()

    # 4. Correct Empty State
    res_empty = client.get(f"/api/v1/requests/{req_id}/matches", headers=borrower_headers)
    assert res_empty.status_code == 200
    assert res_empty.json() == []


# ==============================================================================
# Additional Authorization and Active Exchange Integration Tests
# ==============================================================================


def test_borrow_request_duplicate_and_cancel_guards(client: TestClient, db: Session):
    """Verify duplicate active request rejection (409) and cancellation guards (F-020, F-021)."""
    user = create_user(db, email="student_guards@stu.pes.edu", location="Campus Center")
    token = create_token(user)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create request
    res = client.post(
        "/api/v1/requests",
        json={"isbn": "9780132143011", "location": "Campus Center"},
        headers=headers,
    )
    assert res.status_code == 201
    req_id = res.json()["id"]

    # 2. Duplicate active request returns 409
    res_dup = client.post(
        "/api/v1/requests",
        json={"isbn": "9780132143011", "location": "Campus Center"},
        headers=headers,
    )
    assert res_dup.status_code == 409
    assert "DUPLICATE_ACTIVE_REQUEST" in str(res_dup.json())

    # 3. Non-owner cannot cancel -> 403
    other_user = create_user(db, email="other_student@stu.pes.edu")
    other_token = create_token(other_user)
    res_non_owner_cancel = client.post(
        f"/api/v1/requests/{req_id}/cancel",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert res_non_owner_cancel.status_code == 403

    # 4. Owner cancels -> 200 CANCELLED
    res_cancel = client.post(f"/api/v1/requests/{req_id}/cancel", headers=headers)
    assert res_cancel.status_code == 200
    assert res_cancel.json()["status"] == "CANCELLED"

    # 5. Repeat cancel is idempotent -> 200
    res_repeat = client.post(f"/api/v1/requests/{req_id}/cancel", headers=headers)
    assert res_repeat.status_code == 200


def test_real_active_exchange_delete_guard(client: TestClient, db: Session):
    """Sprint 2 end-to-end integration: real active exchange prevents listing deletion (F-013)."""
    owner = create_user(db, email="active_exchange_real_owner@stu.pes.edu")
    borrower = create_user(db, email="active_exchange_real_borrower@stu.pes.edu")

    owner_token = create_token(owner)
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    listing = create_book_and_listing(
        db,
        owner=owner,
        title="Operating System Concepts",
        author="Silberschatz",
        isbn="9781118063330",
        condition_rank=4,
        location="Lab 1",
    )

    req = BorrowRequest(
        borrower_id=borrower.id, isbn="9781118063330", location="Lab 1", status="OPEN"
    )
    db.add(req)
    db.commit()

    match = Match(
        request_id=req.id,
        listing_id=listing.id,
        score=100.0,
        relevance=1.0,
        status="ACCEPTED",
        borrower_accepted=True,
        lender_accepted=True,
    )
    db.add(match)
    db.commit()

    # Create real active exchange in DB
    exchange = Exchange(
        match_id=match.id,
        request_id=req.id,
        listing_id=listing.id,
        state="ACCEPTED",
    )
    db.add(exchange)
    listing.status = "RESERVED"
    db.commit()

    # Attempt to delete listing with real active exchange -> 409 ACTIVE_EXCHANGE without mock!
    res_del = client.delete(f"/api/v1/listings/{listing.id}", headers=owner_headers)
    assert res_del.status_code == 409
    assert "ACTIVE_EXCHANGE" in str(res_del.json())


def test_new_match_creates_notifications_for_both_participants(db: Session):
    """A newly created match notifies borrower and listing owner."""
    borrower = create_user(db, "borrower_notification@stu.pes.edu")
    lender = create_user(db, "lender_notification@stu.pes.edu")

    create_book_and_listing(
        db,
        owner=lender,
        title="Database System Concepts",
        author="Silberschatz",
        isbn="9780073523323",
        condition_rank=4,
        location="Campus Center",
    )

    request = BorrowRequest(
        borrower_id=borrower.id,
        isbn="9780073523323",
        location="Campus Center",
        status="OPEN",
    )
    db.add(request)
    db.commit()
    db.refresh(request)

    matches = recompute_matches_for_request(db, request)

    assert len(matches) == 1

    notifications = (
        db.query(Notification)
        .filter(Notification.event_key == f"match:{matches[0].id}:found")
        .all()
    )

    assert len(notifications) == 2
    assert {n.user_id for n in notifications} == {borrower.id, lender.id}
    assert all(n.event_type == "MATCH_FOUND" for n in notifications)


def test_recomputing_existing_match_does_not_duplicate_notifications(
    db: Session,
):
    """Repeated matching recomputation must not duplicate MATCH_FOUND notifications."""
    borrower = create_user(db, "borrower_repeat@stu.pes.edu")
    lender = create_user(db, "lender_repeat@stu.pes.edu")

    create_book_and_listing(
        db,
        owner=lender,
        title="Database System Concepts",
        author="Silberschatz",
        isbn="9780073523323",
        condition_rank=4,
        location="Campus Center",
    )

    request = BorrowRequest(
        borrower_id=borrower.id,
        isbn="9780073523323",
        location="Campus Center",
        status="OPEN",
    )
    db.add(request)
    db.commit()
    db.refresh(request)

    first_matches = recompute_matches_for_request(db, request)
    second_matches = recompute_matches_for_request(db, request)

    assert len(first_matches) == 1
    assert len(second_matches) == 1

    count = (
        db.query(Notification)
        .filter(Notification.event_key == f"match:{first_matches[0].id}:found")
        .count()
    )

    assert count == 2


def test_acceptance_creates_partner_decision_notification(db: Session):
    """An acceptance notifies the other match participant."""
    borrower = create_user(db, "borrower_accept@stu.pes.edu")
    lender = create_user(db, "lender_accept@stu.pes.edu")

    listing = create_book_and_listing(
        db,
        owner=lender,
        title="Database System Concepts",
        author="Silberschatz",
        isbn="9780073523323",
        condition_rank=4,
        location="Campus Center",
    )

    request = BorrowRequest(
        borrower_id=borrower.id,
        isbn="9780073523323",
        location="Campus Center",
        status="MATCHED",
    )
    db.add(request)
    db.commit()
    db.refresh(request)

    match = Match(
        request_id=request.id,
        listing_id=listing.id,
        score=100,
        relevance=1,
        status="PROPOSED",
    )
    db.add(match)
    db.commit()
    db.refresh(match)

    handle_match_decision(
        db,
        match_id=match.id,
        current_user_id=borrower.id,
        decision="accept",
    )

    notification = (
        db.query(Notification)
        .filter(
            Notification.user_id == lender.id,
            Notification.event_key == f"match:{match.id}:decision:{borrower.id}:accept",
        )
        .one()
    )

    assert notification.event_type == "PARTNER_DECISION"


def test_decline_creates_partner_decision_notification(db: Session):
    """A decline notifies the other match participant."""
    borrower = create_user(db, "borrower_decline@stu.pes.edu")
    lender = create_user(db, "lender_decline@stu.pes.edu")

    listing = create_book_and_listing(
        db,
        owner=lender,
        title="Database System Concepts",
        author="Silberschatz",
        isbn="9780073523323",
        condition_rank=4,
        location="Campus Center",
    )

    request = BorrowRequest(
        borrower_id=borrower.id,
        isbn="9780073523323",
        location="Campus Center",
        status="MATCHED",
    )
    db.add(request)
    db.commit()
    db.refresh(request)

    match = Match(
        request_id=request.id,
        listing_id=listing.id,
        score=100,
        relevance=1,
        status="PROPOSED",
    )
    db.add(match)
    db.commit()
    db.refresh(match)

    handle_match_decision(
        db,
        match_id=match.id,
        current_user_id=borrower.id,
        decision="decline",
    )

    notification = (
        db.query(Notification)
        .filter(
            Notification.user_id == lender.id,
            Notification.event_key == f"match:{match.id}:decision:{borrower.id}:decline",
        )
        .one()
    )

    assert notification.event_type == "PARTNER_DECISION"


def test_mutual_acceptance_creates_exchange_notifications(db: Session):
    """Mutual acceptance notifies both participants about the exchange."""
    borrower = create_user(db, "borrower_exchange@stu.pes.edu")
    lender = create_user(db, "lender_exchange@stu.pes.edu")

    listing = create_book_and_listing(
        db,
        owner=lender,
        title="Database System Concepts",
        author="Silberschatz",
        isbn="9780073523323",
        condition_rank=4,
        location="Campus Center",
    )

    request = BorrowRequest(
        borrower_id=borrower.id,
        isbn="9780073523323",
        location="Campus Center",
        status="MATCHED",
    )
    db.add(request)
    db.commit()
    db.refresh(request)

    match = Match(
        request_id=request.id,
        listing_id=listing.id,
        score=100,
        relevance=1,
        status="PROPOSED",
    )
    db.add(match)
    db.commit()
    db.refresh(match)

    handle_match_decision(
        db,
        match_id=match.id,
        current_user_id=borrower.id,
        decision="accept",
    )

    result = handle_match_decision(
        db,
        match_id=match.id,
        current_user_id=lender.id,
        decision="accept",
    )

    assert result["status"] == "ACCEPTED"

    notifications = (
        db.query(Notification)
        .filter(Notification.event_key == f"exchange:{result['exchangeId']}:state:ACCEPTED")
        .all()
    )

    assert len(notifications) == 2
    assert {n.user_id for n in notifications} == {borrower.id, lender.id}
    assert all(n.event_type == "EXCHANGE_UPDATED" for n in notifications)
