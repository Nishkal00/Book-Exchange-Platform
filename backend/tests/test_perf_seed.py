"""Tests for performance data seeding, locustfile scenarios, and NF-001 (TC-PERF-01)."""

from __future__ import annotations

import ast
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import jwt
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import get_db
from app.main import app
from app.models import Book, BorrowRequest, Listing, User
from scripts.seed_perf_data import (
    AUTHORS,
    CAMPUS_LOCATIONS,
    DISCIPLINES,
    generate_isbn,
    seed_performance_data,
)


@pytest.fixture
def client(db):
    """TestClient fixture overriding get_db to the test database."""

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_generate_isbn_format():
    """Verify that generate_isbn produces valid 13-digit normalized strings."""
    isbn = generate_isbn(42)
    assert len(isbn) == 13
    assert isbn.startswith("978")
    assert isbn.isdigit()


def test_seed_performance_data_distribution(db):
    """Verify seed_performance_data generates correct user, book, and listing distributions."""
    result = seed_performance_data(
        db=db,
        num_users=5,
        num_books=15,
        num_listings=30,
        clean_first=True,
    )
    assert result["users"] == 5
    assert result["books"] == 15
    assert result["listings"] == 30
    assert result["duration_seconds"] >= 0

    # Verify synthetic users
    users = db.query(User).filter(User.email.like("perf_student_%@example.edu")).all()
    assert len(users) == 5
    for user in users:
        assert user.role == "student"
        assert user.active is True
        assert user.location in CAMPUS_LOCATIONS

    # Verify books
    books = db.query(Book).all()
    assert len(books) == 15
    for book in books:
        assert len(book.isbn) == 13
        assert any(disc in book.title for disc in DISCIPLINES)
        assert any(auth in book.author for auth in AUTHORS)

    # Verify listings
    listings = db.query(Listing).all()
    assert len(listings) == 30
    statuses = {item.status for item in listings}
    assert "AVAILABLE" in statuses


def test_tc_perf_01_search_latency_on_seeded_data(client, db):
    """TC-PERF-01: Verify that search queries against seeded data execute under 2.0s limit."""
    seed_performance_data(
        db=db,
        num_users=5,
        num_books=20,
        num_listings=50,
        clean_first=True,
    )

    test_urls = [
        "/api/v1/listings",
        f"/api/v1/listings?q={DISCIPLINES[0]}",
        f"/api/v1/listings?q={AUTHORS[0]}",
        f"/api/v1/listings?isbn={generate_isbn(1)}",
        f"/api/v1/listings?location={CAMPUS_LOCATIONS[0]}",
        f"/api/v1/listings?q={DISCIPLINES[1]}&location={CAMPUS_LOCATIONS[1]}",
        "/api/v1/listings?page=1&size=10",
    ]

    for url in test_urls:
        t0 = time.perf_counter()
        resp = client.get(url)
        elapsed = time.perf_counter() - t0
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert "page" in body
        assert "size" in body
        assert elapsed < 2.0, f"Query {url} took {elapsed:.3f}s (exceeded 2.0s ceiling)"


def test_locustfile_task_definitions():
    """Verify that locustfile.py defines tasks matching representative traffic."""
    locust_path = Path(__file__).resolve().parent.parent / "locustfile.py"
    assert locust_path.exists()
    tree = ast.parse(locust_path.read_text(encoding="utf-8"))
    class_names = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    assert "ListingSearchUser" in class_names
    func_names = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
    for expected_task in [
        "search_by_title",
        "search_by_author",
        "search_by_isbn",
        "search_by_location",
        "search_combined_filter",
        "browse_pagination",
        "default_search",
    ]:
        assert expected_task in func_names


def test_seed_performance_requests_distribution(db):
    """Verify that seed_performance_data seeds valid open borrow requests (NF-005)."""
    result = seed_performance_data(
        db=db,
        num_users=5,
        num_books=15,
        num_listings=30,
        num_requests=25,
        clean_first=True,
    )
    assert result["users"] == 5
    assert result["books"] == 15
    assert result["listings"] == 30
    assert result["requests"] == 25

    requests = db.query(BorrowRequest).all()
    assert len(requests) == 25
    user_ids = {u.id for u in db.query(User).all()}

    isbn_count = 0
    query_count = 0
    for req in requests:
        assert req.status == "OPEN"
        assert req.borrower_id in user_ids
        assert req.location in CAMPUS_LOCATIONS
        assert req.isbn is not None or (req.query is not None and len(req.query.strip()) > 0)
        if req.isbn is not None:
            isbn_count += 1
        if req.query is not None:
            query_count += 1

    assert isbn_count > 0, "Expected at least one ISBN request"
    assert query_count > 0, "Expected at least one query request"


def test_tc_perf_02_matching_latency_and_correctness(client, db):
    """TC-PERF-02: Verify matching engine produces <=5 candidates at p95 <= 2.0s."""
    seed_performance_data(
        db=db,
        num_users=5,
        num_books=20,
        num_listings=60,
        num_requests=20,
        clean_first=True,
    )

    requests = db.query(BorrowRequest).filter(BorrowRequest.status == "OPEN").all()
    assert len(requests) >= 20

    settings = get_settings()
    users = {u.id: u for u in db.query(User).all()}

    def make_token(user: User) -> str:
        expires_at = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
        return jwt.encode(
            {
                "sub": str(user.id),
                "email": user.email,
                "role": user.role,
                "ver": user.token_version,
                "exp": expires_at,
            },
            settings.jwt_secret,
            algorithm="HS256",
        )

    latencies = []
    for req in requests:
        user = users[req.borrower_id]
        token = make_token(user)
        headers = {"Authorization": f"Bearer {token}"}

        t0 = time.perf_counter()
        resp = client.get(f"/api/v1/requests/{req.id}/matches", headers=headers)
        elapsed = time.perf_counter() - t0
        latencies.append(elapsed)

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert len(data) <= 5, f"Candidate count {len(data)} exceeded maximum of 5"

        # Verify candidate ranking is deterministically ordered by descending score
        if len(data) > 1:
            scores = [m["score"] for m in data]
            assert scores == sorted(scores, reverse=True), (
                "Candidates not sorted by descending score"
            )

        # Verify candidate listings are not owned by the borrower
        for match_item in data:
            listing = match_item["listing"]
            assert listing["owner_id"] != req.borrower_id, "Candidate listing belongs to borrower"
            assert listing["status"] == "AVAILABLE", "Candidate listing is not AVAILABLE"

    # Evaluate p95 latency
    latencies.sort()
    p95_idx = int(len(latencies) * 0.95)
    p95 = latencies[p95_idx]
    assert p95 <= 2.0, f"TC-PERF-02 failed: p95 latency {p95:.4f}s exceeded 2.0s limit"


def test_tc_perf_02_concurrency_race_safety(tmp_path):
    """TC-PERF-02: Verify concurrent matching evaluations execute cleanly without races or locks."""
    from sqlalchemy.orm import sessionmaker

    from app.database import Base, make_engine
    from app.services.matching import get_candidate_listings

    db_path = tmp_path / "test_concurrency.db"
    engine = make_engine(
        f"sqlite:///{db_path.resolve()}",
        connect_args={"timeout": 30},
    )
    with engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA journal_mode=WAL;")
        conn.exec_driver_sql("PRAGMA busy_timeout=30000;")

    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)

    init_session = session_factory()
    try:
        seed_performance_data(
            db=init_session,
            num_users=5,
            num_books=20,
            num_listings=50,
            num_requests=15,
            clean_first=True,
        )
        request_ids = [
            r.id
            for r in init_session.query(BorrowRequest).filter(BorrowRequest.status == "OPEN").all()
        ]
    finally:
        init_session.close()

    def evaluate_request_concurrently(req_id: int) -> int:
        session = session_factory()
        try:
            req_item = session.get(BorrowRequest, req_id)
            cands = get_candidate_listings(session, req_item)
            return len(cands)
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=5) as executor:
        candidate_counts = list(executor.map(evaluate_request_concurrently, request_ids))

    assert len(candidate_counts) == len(request_ids)
    for count in candidate_counts:
        assert 0 <= count <= 5

    engine.dispose()
