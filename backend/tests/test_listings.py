from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import get_db
from app.main import app
from app.models import Book, Listing, User


def create_test_user(db, email="student@example.edu", active=True, token_version=0) -> User:
    """Helper to create and commit a test user."""
    user = User(
        name="Listing Student",
        email=email,
        password_hash="hashed_pw_test",
        role="student",
        location="Campus Center",
        active=active,
        token_version=token_version,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_auth_token(user: User, expires_in_minutes=30, version=None) -> str:
    """Helper to create a valid JWT for an authenticated user."""
    settings = get_settings()
    expires_at = datetime.now(UTC) + timedelta(minutes=expires_in_minutes)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "exp": expires_at,
    }
    if version is not None:
        payload["ver"] = version
    else:
        payload["ver"] = user.token_version
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


@pytest.fixture
def client(db):
    """TestClient fixture with get_db dependency overridden to the test database."""

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ==============================================================================
# TC-LST-01: Authenticated owner creates listing & book reuse by normalized ISBN
# ==============================================================================


def test_tc_lst_01_create_listing_success_and_book_reuse(client, db):
    """TC-LST-01: Authenticated owner creates valid listing -> 201 AVAILABLE.
    Repeat ISBN for another copy: one book, separate listing.
    No token -> 401.
    """
    owner1 = create_test_user(db, email="owner1@example.edu")
    owner2 = create_test_user(db, email="owner2@example.edu")
    token1 = create_auth_token(owner1)
    token2 = create_auth_token(owner2)

    headers1 = {"Authorization": f"Bearer {token1}"}
    headers2 = {"Authorization": f"Bearer {token2}"}

    # 1. Unauthenticated request (no token) must fail with 401
    unauth_resp = client.post(
        "/api/v1/listings",
        json={
            "title": "Clean Code",
            "author": "Robert C. Martin",
            "isbn": "978-0-13-235088-4",
            "condition": "GOOD",
            "location": "Library A",
        },
    )
    assert unauth_resp.status_code == 401

    # 2. Owner 1 creates valid listing -> 201 with status AVAILABLE
    payload1 = {
        "title": "Clean Code",
        "author": "Robert C. Martin",
        "isbn": "978-0-13-235088-4",  # ISBN with hyphens
        "condition": "GOOD",
        "location": "Library A",
    }
    res1 = client.post("/api/v1/listings", headers=headers1, json=payload1)
    assert res1.status_code == 201
    data1 = res1.json()

    assert data1["status"] == "AVAILABLE"
    assert data1["title"] == "Clean Code"
    assert data1["author"] == "Robert C. Martin"
    assert data1["isbn"] == "9780132350884"  # Hyphens removed
    assert data1["condition"] == "GOOD"
    assert data1["location"] == "Library A"
    assert data1["owner_id"] == owner1.id
    assert data1["ownerId"] == owner1.id
    assert "id" in data1
    assert "created_at" in data1
    assert "createdAt" in data1

    # Secrets and contact details must NOT be exposed
    assert "password" not in data1
    assert "password_hash" not in data1
    assert "email" not in data1
    assert "token_version" not in data1

    # Check database state: 1 book, 1 listing
    books = db.query(Book).all()
    listings = db.query(Listing).all()
    assert len(books) == 1
    assert books[0].isbn == "9780132350884"
    assert len(listings) == 1
    assert listings[0].owner_id == owner1.id
    assert listings[0].book_id == books[0].id
    assert listings[0].status == "AVAILABLE"
    assert listings[0].condition_rank == 3  # GOOD -> rank 3

    # 3. Repeat ISBN for another copy (by owner 2): one book, separate listing
    payload2 = {
        "title": "Clean Code (Second Copy)",
        "author": "Robert Martin",
        "isbn": "9780132350884",  # Same normalized ISBN without hyphens
        "condition": "NEW",
        "location": "North Campus",
    }
    res2 = client.post("/api/v1/listings", headers=headers2, json=payload2)
    assert res2.status_code == 201
    data2 = res2.json()

    assert data2["id"] != data1["id"]
    assert data2["status"] == "AVAILABLE"
    assert data2["condition"] == "NEW"
    assert data2["location"] == "North Campus"
    assert data2["owner_id"] == owner2.id

    # Verify only ONE book exists, reused across both listings
    all_books = db.query(Book).all()
    all_listings = db.query(Listing).all()
    assert len(all_books) == 1
    assert len(all_listings) == 2
    assert all_listings[0].book_id == all_books[0].id
    assert all_listings[1].book_id == all_books[0].id
    assert all_listings[0].id != all_listings[1].id


def test_tc_lst_01_token_validation_variants(client, db):
    """Test invalid token, expired token, revoked token, and inactive user return 401."""
    user = create_test_user(db, email="student_token@example.edu")
    valid_payload = {
        "title": "Design Patterns",
        "author": "Gang of Four",
        "isbn": "0-201-63361-2",
        "condition": "FAIR",
        "location": "Eng Block",
    }

    # Malformed token
    res_bad = client.post(
        "/api/v1/listings",
        headers={"Authorization": "Bearer not-a-valid-token"},
        json=valid_payload,
    )
    assert res_bad.status_code == 401

    # Invalid scheme
    res_scheme = client.post(
        "/api/v1/listings",
        headers={"Authorization": "Basic 123456"},
        json=valid_payload,
    )
    assert res_scheme.status_code == 401

    # Expired token
    expired_token = create_auth_token(user, expires_in_minutes=-10)
    res_expired = client.post(
        "/api/v1/listings",
        headers={"Authorization": f"Bearer {expired_token}"},
        json=valid_payload,
    )
    assert res_expired.status_code == 401

    # Token version mismatch (revoked token)
    revoked_token = create_auth_token(user, version=999)
    res_revoked = client.post(
        "/api/v1/listings",
        headers={"Authorization": f"Bearer {revoked_token}"},
        json=valid_payload,
    )
    assert res_revoked.status_code == 401

    # Inactive user
    inactive_user = create_test_user(db, email="inactive@example.edu", active=False)
    inactive_token = create_auth_token(inactive_user)
    res_inactive = client.post(
        "/api/v1/listings",
        headers={"Authorization": f"Bearer {inactive_token}"},
        json=valid_payload,
    )
    assert res_inactive.status_code == 401


# ==============================================================================
# TC-LST-02: Field-level validation on title, ISBN, condition, author, location
# ==============================================================================


def test_tc_lst_02_field_validations(client, db):
    """TC-LST-02: Send empty title, invalid ISBN length or invalid condition separately.
    Expect 422 naming field; no listing inserted.
    """
    user = create_test_user(db, email="validator@example.edu")
    token = create_auth_token(user)
    headers = {"Authorization": f"Bearer {token}"}

    base_payload = {
        "title": "Introduction to Algorithms",
        "author": "Cormen, Leiserson, Rivest, Stein",
        "isbn": "978-0-262-03384-8",
        "condition": "NEW",
        "location": "Main Library",
    }

    # Baseline check: 0 books and 0 listings
    assert db.query(Listing).count() == 0
    assert db.query(Book).count() == 0

    # 1. Empty title -> 422 naming 'title'
    p = dict(base_payload, title="")
    res = client.post("/api/v1/listings", headers=headers, json=p)
    assert res.status_code == 422
    assert any(
        "title" in str(loc) for err in res.json().get("detail", []) for loc in err.get("loc", [])
    )
    assert db.query(Listing).count() == 0

    # Whitespace-only title -> 422
    p = dict(base_payload, title="   ")
    res = client.post("/api/v1/listings", headers=headers, json=p)
    assert res.status_code == 422
    assert any(
        "title" in str(loc) for err in res.json().get("detail", []) for loc in err.get("loc", [])
    )
    assert db.query(Listing).count() == 0

    # Title > 200 chars -> 422
    p = dict(base_payload, title="A" * 201)
    res = client.post("/api/v1/listings", headers=headers, json=p)
    assert res.status_code == 422
    assert any(
        "title" in str(loc) for err in res.json().get("detail", []) for loc in err.get("loc", [])
    )
    assert db.query(Listing).count() == 0

    # 2. Invalid ISBN length: 9 digits -> 422 naming 'isbn'
    p = dict(base_payload, isbn="123456789")
    res = client.post("/api/v1/listings", headers=headers, json=p)
    assert res.status_code == 422
    assert any(
        "isbn" in str(loc) for err in res.json().get("detail", []) for loc in err.get("loc", [])
    )
    assert db.query(Listing).count() == 0

    # Invalid ISBN length: 11 digits -> 422
    p = dict(base_payload, isbn="12345678901")
    res = client.post("/api/v1/listings", headers=headers, json=p)
    assert res.status_code == 422
    assert any(
        "isbn" in str(loc) for err in res.json().get("detail", []) for loc in err.get("loc", [])
    )
    assert db.query(Listing).count() == 0

    # Invalid ISBN length: 14 digits -> 422
    p = dict(base_payload, isbn="12345678901234")
    res = client.post("/api/v1/listings", headers=headers, json=p)
    assert res.status_code == 422
    assert any(
        "isbn" in str(loc) for err in res.json().get("detail", []) for loc in err.get("loc", [])
    )
    assert db.query(Listing).count() == 0

    # ISBN with non-digits after hyphen removal -> 422
    p = dict(base_payload, isbn="978-0-13-110362-X")
    res = client.post("/api/v1/listings", headers=headers, json=p)
    assert res.status_code == 422
    assert any(
        "isbn" in str(loc) for err in res.json().get("detail", []) for loc in err.get("loc", [])
    )
    assert db.query(Listing).count() == 0

    # 3. Invalid condition -> 422 naming 'condition'
    for bad_cond in ["MINT", "EXCELLENT", "POORLY", "LIKE_NEW", "", "123"]:
        p = dict(base_payload, condition=bad_cond)
        res = client.post("/api/v1/listings", headers=headers, json=p)
        assert res.status_code == 422
        assert any(
            "condition" in str(loc)
            for err in res.json().get("detail", [])
            for loc in err.get("loc", [])
        )
        assert db.query(Listing).count() == 0

    # 4. Author empty or > 150 chars -> 422 naming 'author'
    p = dict(base_payload, author="")
    res = client.post("/api/v1/listings", headers=headers, json=p)
    assert res.status_code == 422
    assert any(
        "author" in str(loc) for err in res.json().get("detail", []) for loc in err.get("loc", [])
    )
    assert db.query(Listing).count() == 0

    p = dict(base_payload, author="B" * 151)
    res = client.post("/api/v1/listings", headers=headers, json=p)
    assert res.status_code == 422
    assert any(
        "author" in str(loc) for err in res.json().get("detail", []) for loc in err.get("loc", [])
    )
    assert db.query(Listing).count() == 0

    # 5. Location empty or > 100 chars -> 422 naming 'location'
    p = dict(base_payload, location="")
    res = client.post("/api/v1/listings", headers=headers, json=p)
    assert res.status_code == 422
    assert any(
        "location" in str(loc) for err in res.json().get("detail", []) for loc in err.get("loc", [])
    )
    assert db.query(Listing).count() == 0

    p = dict(base_payload, location="C" * 101)
    res = client.post("/api/v1/listings", headers=headers, json=p)
    assert res.status_code == 422
    assert any(
        "location" in str(loc) for err in res.json().get("detail", []) for loc in err.get("loc", [])
    )
    assert db.query(Listing).count() == 0

    # Verify that throughout all invalid attempts, zero listings and zero books were inserted
    assert db.query(Listing).count() == 0
    assert db.query(Book).count() == 0


def test_tc_lst_02_all_allowed_conditions(client, db):
    """Verify that all allowed conditions (NEW, GOOD, FAIR, POOR) are accepted and mapped."""
    user = create_test_user(db, email="cond_tester@example.edu")
    token = create_auth_token(user)
    headers = {"Authorization": f"Bearer {token}"}

    conditions = [("NEW", 4), ("GOOD", 3), ("FAIR", 2), ("POOR", 1)]
    for i, (cond, expected_rank) in enumerate(conditions):
        isbn = f"978000000000{i}"
        res = client.post(
            "/api/v1/listings",
            headers=headers,
            json={
                "title": f"Book on {cond}",
                "author": "Condition Author",
                "isbn": isbn,
                "condition": cond,
                "location": "Hostel B",
            },
        )
        assert res.status_code == 201
        data = res.json()
        assert data["condition"] == cond
        listing = db.query(Listing).filter_by(id=data["id"]).one()
        assert listing.condition_rank == expected_rank


# ==============================================================================
# TC-SEC-04: Safe parameterized queries & text rendering of HTML/SQL payloads
# ==============================================================================


def test_tc_sec_04_sql_and_html_injection_safety(client, db):
    """TC-SEC-04 (SR-004): Use SQL-like payloads in title/location/author.
    They are treated as literal data or validation errors, never query syntax;
    no unrelated rows or SQL errors. HTML-looking titles render as text.
    """
    user = create_test_user(db, email="sec_user@example.edu")
    token = create_auth_token(user)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. SQL injection payload in title
    sql_payload_title = "The C Book'; DROP TABLE listings; --"
    res1 = client.post(
        "/api/v1/listings",
        headers=headers,
        json={
            "title": sql_payload_title,
            "author": "Dennis Ritchie",
            "isbn": "9780131103627",
            "condition": "GOOD",
            "location": "Room 404",
        },
    )
    assert res1.status_code == 201
    data1 = res1.json()
    assert data1["title"] == sql_payload_title  # Stored verbatim as literal text

    # Verify tables still exist and contain the literal data
    listing1 = db.query(Listing).filter_by(id=data1["id"]).one()
    assert listing1.book.title == sql_payload_title

    # 2. SQL injection payload in location
    sql_payload_location = "Hostel 3' OR '1'='1"
    res2 = client.post(
        "/api/v1/listings",
        headers=headers,
        json={
            "title": "Operating Systems",
            "author": "Silberschatz",
            "isbn": "9781118063330",
            "condition": "NEW",
            "location": sql_payload_location,
        },
    )
    assert res2.status_code == 201
    data2 = res2.json()
    assert data2["location"] == sql_payload_location

    listing2 = db.query(Listing).filter_by(id=data2["id"]).one()
    assert listing2.location == sql_payload_location

    # 3. SQL injection payload in author
    sql_payload_author = "Author' UNION SELECT * FROM users --"
    res3 = client.post(
        "/api/v1/listings",
        headers=headers,
        json={
            "title": "Computer Networks",
            "author": sql_payload_author,
            "isbn": "9780132126953",
            "condition": "FAIR",
            "location": "Lab 2",
        },
    )
    assert res3.status_code == 201
    data3 = res3.json()
    assert data3["author"] == sql_payload_author

    # 4. SQL injection in ISBN -> fails validation because ISBN must be 10 or 13 digits
    res_sql_isbn = client.post(
        "/api/v1/listings",
        headers=headers,
        json={
            "title": "Security Book",
            "author": "Sec Author",
            "isbn": "1234567890'; DROP TABLE users; --",
            "condition": "GOOD",
            "location": "Campus Center",
        },
    )
    assert res_sql_isbn.status_code == 422
    assert any(
        "isbn" in str(loc)
        for err in res_sql_isbn.json().get("detail", [])
        for loc in err.get("loc", [])
    )

    # 5. HTML content in title and author rendered as literal text
    html_title = "<script>alert('XSS')</script><b>Database Systems</b>"
    html_author = "<img src=x onerror=alert(1)> Elmasri"
    res4 = client.post(
        "/api/v1/listings",
        headers=headers,
        json={
            "title": html_title,
            "author": html_author,
            "isbn": "9780136086208",
            "condition": "POOR",
            "location": "Corner Store",
        },
    )
    assert res4.status_code == 201
    data4 = res4.json()
    # Stored and returned as pure literal strings without interpretation
    assert data4["title"] == html_title
    assert data4["author"] == html_author
