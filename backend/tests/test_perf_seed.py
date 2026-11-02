"""Tests for performance data seeding, locustfile scenarios, and NF-001 (TC-PERF-01)."""

from __future__ import annotations

import ast
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import Book, Listing, User
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
