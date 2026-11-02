import time
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


def create_test_listing(
    db,
    owner: User,
    title: str,
    author: str,
    isbn: str,
    condition_rank: int = 3,
    location: str = "Main Library",
    status: str = "AVAILABLE",
    deleted_at: datetime | None = None,
) -> Listing:
    """Helper to seed a Book and Listing directly in the test database."""
    book = db.query(Book).filter_by(isbn=isbn).first()
    if not book:
        book = Book(title=title, author=author, isbn=isbn)
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
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


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


# ==============================================================================
# TC-LST-03: Public search of AVAILABLE, non-deleted listings by q, ISBN, location
# ==============================================================================


def test_tc_lst_03_search_filters_and_availability(client, db):
    """TC-LST-03: Publicly search AVAILABLE, non-deleted listings by title/author q,
    ISBN, and location with pagination. Only qualifying AVAILABLE non-deleted listings appear.
    """
    owner1 = create_test_user(db, email="owner_search1@example.edu")
    owner2 = create_test_user(db, email="owner_search2@example.edu")

    # Listing 1: AVAILABLE, Clean Architecture by Robert C. Martin
    l1 = create_test_listing(
        db,
        owner=owner1,
        title="Clean Architecture",
        author="Robert C. Martin",
        isbn="9780134494166",
        condition_rank=4,
        location="Main Library",
        status="AVAILABLE",
    )
    # Listing 2: AVAILABLE, Introduction to Algorithms by Thomas Cormen
    l2 = create_test_listing(
        db,
        owner=owner1,
        title="Introduction to Algorithms",
        author="Thomas Cormen",
        isbn="9780262033848",
        condition_rank=3,
        location="Engineering Hall",
        status="AVAILABLE",
    )
    # Listing 3: AVAILABLE, Design Patterns by Erich Gamma
    l3 = create_test_listing(
        db,
        owner=owner2,
        title="Design Patterns",
        author="Erich Gamma",
        isbn="9780201633610",
        condition_rank=2,
        location="Campus Center",
        status="AVAILABLE",
    )
    # Listing 4: UNAVAILABLE, Refactoring by Martin Fowler
    # (author matches 'Martin' but status is UNAVAILABLE)
    create_test_listing(
        db,
        owner=owner2,
        title="Refactoring",
        author="Martin Fowler",
        isbn="9780201485677",
        condition_rank=1,
        location="Main Library",
        status="UNAVAILABLE",
    )
    # Listing 5: SOFT-DELETED, Clean Code (matches 'Clean' and 'Main Library' but soft-deleted)
    create_test_listing(
        db,
        owner=owner1,
        title="Clean Code",
        author="Robert C. Martin",
        isbn="9780132350884",
        condition_rank=3,
        location="Main Library",
        status="AVAILABLE",
        deleted_at=datetime.now(UTC),
    )
    # Listing 6: RESERVED status (location matches 'Engineering Hall' but status is RESERVED)
    create_test_listing(
        db,
        owner=owner2,
        title="Database Concepts",
        author="Silberschatz",
        isbn="9780073523323",
        condition_rank=3,
        location="Engineering Hall",
        status="RESERVED",
    )
    # Listing 7: ON_LOAN status
    create_test_listing(
        db,
        owner=owner2,
        title="Operating Systems",
        author="Silberschatz",
        isbn="9781118063330",
        condition_rank=3,
        location="Engineering Hall",
        status="ON_LOAN",
    )

    # 1. Search by title q ('Clean') -> only AVAILABLE, non-deleted Listing 1 appears
    res_q_title = client.get("/api/v1/listings?q=clean")
    assert res_q_title.status_code == 200
    data = res_q_title.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == l1.id
    assert data["items"][0]["title"] == "Clean Architecture"
    assert data["items"][0]["condition"] == "NEW"
    assert data["items"][0]["status"] == "AVAILABLE"
    # Verify public schema omits secrets/contact details
    assert "email" not in data["items"][0]
    assert "password" not in data["items"][0]
    assert "token_version" not in data["items"][0]

    # 2. Search by author q ('Cormen') -> only Listing 2 appears
    res_q_author = client.get("/api/v1/listings?q=cormen")
    assert res_q_author.status_code == 200
    data_author = res_q_author.json()
    assert data_author["total"] == 1
    assert len(data_author["items"]) == 1
    assert data_author["items"][0]["id"] == l2.id
    assert data_author["items"][0]["author"] == "Thomas Cormen"

    # 3. Search by author q ('Martin') -> matches l1 (AVAILABLE) and l4 (UNAVAILABLE)
    # Only AVAILABLE l1 must appear; UNAVAILABLE l4 must NOT appear
    res_q_martin = client.get("/api/v1/listings?q=martin")
    assert res_q_martin.status_code == 200
    data_martin = res_q_martin.json()
    assert data_martin["total"] == 1
    assert data_martin["items"][0]["id"] == l1.id

    # 4. Search by exact ISBN without hyphens
    res_isbn = client.get("/api/v1/listings?isbn=9780201633610")
    assert res_isbn.status_code == 200
    data_isbn = res_isbn.json()
    assert data_isbn["total"] == 1
    assert data_isbn["items"][0]["id"] == l3.id
    assert data_isbn["items"][0]["isbn"] == "9780201633610"

    # 5. Search by ISBN with hyphens
    res_isbn_hyphen = client.get("/api/v1/listings?isbn=978-0-201-63361-0")
    assert res_isbn_hyphen.status_code == 200
    assert res_isbn_hyphen.json()["total"] == 1
    assert res_isbn_hyphen.json()["items"][0]["id"] == l3.id

    # 6. Search by location ('Engineering Hall')
    # Matches l2 (AVAILABLE), but l6 (RESERVED) and l7 (ON_LOAN) must be excluded
    res_loc = client.get("/api/v1/listings?location=Engineering Hall")
    assert res_loc.status_code == 200
    data_loc = res_loc.json()
    assert data_loc["total"] == 1
    assert data_loc["items"][0]["id"] == l2.id

    # Case-insensitive/partial location search ('main')
    # Matches l1 (AVAILABLE), but l4 (UNAVAILABLE) and l5 (deleted) must be excluded
    res_loc_partial = client.get("/api/v1/listings?location=main")
    assert res_loc_partial.status_code == 200
    data_loc_partial = res_loc_partial.json()
    assert data_loc_partial["total"] == 1
    assert data_loc_partial["items"][0]["id"] == l1.id

    # 7. Combined filters (q + location matching l1)
    res_comb1 = client.get("/api/v1/listings?q=architecture&location=Main Library")
    assert res_comb1.status_code == 200
    assert res_comb1.json()["total"] == 1
    assert res_comb1.json()["items"][0]["id"] == l1.id

    # Combined filters with no intersection (q='clean' but location='Campus Center')
    res_comb2 = client.get("/api/v1/listings?q=clean&location=Campus Center")
    assert res_comb2.status_code == 200
    assert res_comb2.json()["total"] == 0
    assert res_comb2.json()["items"] == []

    # Combined filters (q + isbn + location matching l1)
    res_comb3 = client.get("/api/v1/listings?q=Clean&isbn=978-0-13-449416-6&location=Main Library")
    assert res_comb3.status_code == 200
    assert res_comb3.json()["total"] == 1
    assert res_comb3.json()["items"][0]["id"] == l1.id


# ==============================================================================
# TC-LST-04: Pagination limits, empty query results, stable tie ordering
# ==============================================================================


def test_tc_lst_04_pagination_limits_and_empty_results(client, db):
    """TC-LST-04: Unknown query -> 200 empty items.
    Compare page 1/2 slices and total; size=101 and page=0 -> 422; tie ordering stable.
    """
    owner = create_test_user(db, email="pager_owner@example.edu")

    # 1. Unknown query returns 200 with empty items list (F-011)
    res_unknown_q = client.get("/api/v1/listings?q=nonexistent_query_xyz")
    assert res_unknown_q.status_code == 200
    data_unknown = res_unknown_q.json()
    assert data_unknown["items"] == []
    assert data_unknown["total"] == 0
    assert data_unknown["page"] == 1
    assert data_unknown["size"] == 20

    res_unknown_isbn = client.get("/api/v1/listings?isbn=9999999999999")
    assert res_unknown_isbn.status_code == 200
    assert res_unknown_isbn.json()["items"] == []
    assert res_unknown_isbn.json()["total"] == 0

    res_unknown_loc = client.get("/api/v1/listings?location=UnknownLocation77")
    assert res_unknown_loc.status_code == 200
    assert res_unknown_loc.json()["items"] == []
    assert res_unknown_loc.json()["total"] == 0

    # 2. Validation bounds: size=101 and page=0 -> 422 (F-011)
    res_page_zero = client.get("/api/v1/listings?page=0")
    assert res_page_zero.status_code == 422

    res_page_neg = client.get("/api/v1/listings?page=-1")
    assert res_page_neg.status_code == 422

    res_size_too_large = client.get("/api/v1/listings?size=101")
    assert res_size_too_large.status_code == 422

    res_size_zero = client.get("/api/v1/listings?size=0")
    assert res_size_zero.status_code == 422

    res_page_invalid = client.get("/api/v1/listings?page=not_a_number")
    assert res_page_invalid.status_code == 422

    # 3. Default pagination values (page=1, size=20)
    res_defaults = client.get("/api/v1/listings")
    assert res_defaults.status_code == 200
    assert res_defaults.json()["page"] == 1
    assert res_defaults.json()["size"] == 20

    # 4. Seed 5 distinct listings to test page slices, total, and stable tie ordering
    created_listings = []
    for i in range(5):
        lst = create_test_listing(
            db,
            owner=owner,
            title=f"Paged Book Volume {i + 1}",
            author=f"Author {i + 1}",
            isbn=f"97810000000{i:02d}",
            condition_rank=3,
            location="Library Shelf",
            status="AVAILABLE",
        )
        created_listings.append(lst)

    # Fetch all items in a single page
    res_all = client.get("/api/v1/listings?page=1&size=10")
    assert res_all.status_code == 200
    all_data = res_all.json()
    assert all_data["total"] == 5
    assert len(all_data["items"]) == 5

    # Fetch page 1 (size=2)
    res_p1 = client.get("/api/v1/listings?page=1&size=2")
    assert res_p1.status_code == 200
    p1_data = res_p1.json()
    assert p1_data["page"] == 1
    assert p1_data["size"] == 2
    assert p1_data["total"] == 5
    assert len(p1_data["items"]) == 2

    # Fetch page 2 (size=2)
    res_p2 = client.get("/api/v1/listings?page=2&size=2")
    assert res_p2.status_code == 200
    p2_data = res_p2.json()
    assert p2_data["page"] == 2
    assert p2_data["size"] == 2
    assert p2_data["total"] == 5
    assert len(p2_data["items"]) == 2

    # Fetch page 3 (size=2)
    res_p3 = client.get("/api/v1/listings?page=3&size=2")
    assert res_p3.status_code == 200
    p3_data = res_p3.json()
    assert p3_data["page"] == 3
    assert p3_data["size"] == 2
    assert p3_data["total"] == 5
    assert len(p3_data["items"]) == 1

    # Compare page 1, 2, 3 slices to full result
    combined_items = p1_data["items"] + p2_data["items"] + p3_data["items"]
    assert len(combined_items) == 5
    assert [it["id"] for it in combined_items] == [it["id"] for it in all_data["items"]]

    # Ensure no duplicate items across pages
    p1_ids = {it["id"] for it in p1_data["items"]}
    p2_ids = {it["id"] for it in p2_data["items"]}
    p3_ids = {it["id"] for it in p3_data["items"]}
    assert p1_ids.isdisjoint(p2_ids)
    assert p1_ids.isdisjoint(p3_ids)
    assert p2_ids.isdisjoint(p3_ids)

    # Verify tie ordering stability by re-requesting pages
    res_p1_repeat = client.get("/api/v1/listings?page=1&size=2")
    assert [it["id"] for it in res_p1_repeat.json()["items"]] == [
        it["id"] for it in p1_data["items"]
    ]


# ==============================================================================
# TC-LST-08: Authenticated /listings/mine returns caller's non-deleted listings
# ==============================================================================


def test_tc_lst_08_my_listings_isolation_and_statuses(client, db):
    """TC-LST-08: Create listings for A and B including unavailable/deleted entries.
    A calls mine: only A non-deleted listings, including unavailable; no token -> 401.
    """
    user_a = create_test_user(db, email="user_a@example.edu")
    user_b = create_test_user(db, email="user_b@example.edu")
    token_a = create_auth_token(user_a)
    token_b = create_auth_token(user_b)
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A creates listings:
    # A1: AVAILABLE
    a1 = create_test_listing(
        db,
        owner=user_a,
        title="Book A1",
        author="Author A",
        isbn="9780000000101",
        status="AVAILABLE",
    )
    # A2: UNAVAILABLE (must be included in mine)
    a2 = create_test_listing(
        db,
        owner=user_a,
        title="Book A2",
        author="Author A",
        isbn="9780000000102",
        status="UNAVAILABLE",
    )
    # A3: RESERVED (must be included in mine)
    a3 = create_test_listing(
        db,
        owner=user_a,
        title="Book A3",
        author="Author A",
        isbn="9780000000103",
        status="RESERVED",
    )
    # A4: ON_LOAN (must be included in mine)
    a4 = create_test_listing(
        db,
        owner=user_a,
        title="Book A4",
        author="Author A",
        isbn="9780000000104",
        status="ON_LOAN",
    )
    # A5: Soft-deleted (must NOT be included in mine)
    create_test_listing(
        db,
        owner=user_a,
        title="Book A5 Deleted",
        author="Author A",
        isbn="9780000000105",
        status="AVAILABLE",
        deleted_at=datetime.now(UTC),
    )

    # User B creates listings:
    # B1: AVAILABLE
    b1 = create_test_listing(
        db,
        owner=user_b,
        title="Book B1",
        author="Author B",
        isbn="9780000000201",
        status="AVAILABLE",
    )
    # B2: UNAVAILABLE
    b2 = create_test_listing(
        db,
        owner=user_b,
        title="Book B2",
        author="Author B",
        isbn="9780000000202",
        status="UNAVAILABLE",
    )
    # B3: Soft-deleted
    create_test_listing(
        db,
        owner=user_b,
        title="Book B3 Deleted",
        author="Author B",
        isbn="9780000000203",
        status="AVAILABLE",
        deleted_at=datetime.now(UTC),
    )

    # 1. Unauthenticated request -> 401
    res_no_auth = client.get("/api/v1/listings/mine")
    assert res_no_auth.status_code == 401

    res_bad_token = client.get(
        "/api/v1/listings/mine",
        headers={"Authorization": "Bearer not-a-valid-token"},
    )
    assert res_bad_token.status_code == 401

    # 2. User A calls mine: returns only User A's non-deleted listings (4 entries)
    res_mine_a = client.get("/api/v1/listings/mine", headers=headers_a)
    assert res_mine_a.status_code == 200
    data_a = res_mine_a.json()
    assert data_a["total"] == 4
    assert len(data_a["items"]) == 4

    returned_a_ids = {it["id"] for it in data_a["items"]}
    assert returned_a_ids == {a1.id, a2.id, a3.id, a4.id}
    # Verify User B's listings are not present
    assert b1.id not in returned_a_ids
    assert b2.id not in returned_a_ids
    # Verify all returned listings belong to User A
    assert all(it["owner_id"] == user_a.id for it in data_a["items"])
    assert all(it["ownerId"] == user_a.id for it in data_a["items"])

    # Verify unavailable, reserved, and on-loan statuses are included
    statuses_a = {it["status"] for it in data_a["items"]}
    assert statuses_a == {"AVAILABLE", "UNAVAILABLE", "RESERVED", "ON_LOAN"}

    # 3. User B calls mine: returns only User B's non-deleted listings (2 entries)
    res_mine_b = client.get("/api/v1/listings/mine", headers=headers_b)
    assert res_mine_b.status_code == 200
    data_b = res_mine_b.json()
    assert data_b["total"] == 2
    assert len(data_b["items"]) == 2
    returned_b_ids = {it["id"] for it in data_b["items"]}
    assert returned_b_ids == {b1.id, b2.id}
    assert all(it["owner_id"] == user_b.id for it in data_b["items"])

    # 4. Pagination validation on /listings/mine
    res_mine_page_zero = client.get(
        "/api/v1/listings/mine?page=0",
        headers=headers_a,
    )
    assert res_mine_page_zero.status_code == 422

    res_mine_size_too_large = client.get(
        "/api/v1/listings/mine?size=101",
        headers=headers_a,
    )
    assert res_mine_size_too_large.status_code == 422

    # Paginated slice for user A (page 1, size 2)
    res_mine_slice = client.get(
        "/api/v1/listings/mine?page=1&size=2",
        headers=headers_a,
    )
    assert res_mine_slice.status_code == 200
    slice_data = res_mine_slice.json()
    assert slice_data["total"] == 4
    assert len(slice_data["items"]) == 2


# ==============================================================================
# TC-PERF-01: Search performance baseline and latency smoke (NF-001)
# ==============================================================================


def test_tc_perf_01_search_performance_smoke(client, db):
    """TC-PERF-01 (NF-001): The search API shall achieve p90 response time <=2 seconds.
    Per project specification, full search load measurements (50 users, 10/s ramp,
    1 minute run, 10,000 listings, ~2,000 books) are evaluated in story S1-13.
    This smoke test validates endpoint latency baseline, query efficiency, and response
    envelope integrity under standard operations.
    """
    owner = create_test_user(db, email="perf_owner@example.edu")
    for i in range(25):
        create_test_listing(
            db,
            owner=owner,
            title=f"Scalability Engineering Volume {i + 1}",
            author=f"Performance Author {i % 5}",
            isbn=f"97820000000{i:02d}",
            condition_rank=3,
            location=f"Branch {i % 3}",
            status="AVAILABLE",
        )

    latencies: list[float] = []
    test_queries = [
        "/api/v1/listings",
        "/api/v1/listings?q=Engineering",
        "/api/v1/listings?q=Author 1",
        "/api/v1/listings?isbn=9782000000005",
        "/api/v1/listings?location=Branch 0",
        "/api/v1/listings?q=Volume&location=Branch 1&page=1&size=10",
        "/api/v1/listings?q=NonexistentQuery",
    ]

    for path in test_queries:
        start_time = time.perf_counter()
        res = client.get(path)
        elapsed = time.perf_counter() - start_time
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        latencies.append(elapsed)

    # All search queries should complete well within the <= 2.0s NF-001 threshold
    for latency in latencies:
        assert latency < 2.0, f"Query latency {latency:.3f}s exceeded 2.0s limit"


# ==============================================================================
# TC-LST-05: Owner changes condition/status, lifecycle guards, missing IDs (F-012)
# ==============================================================================


def test_tc_lst_05_update_listing_owner_status_and_lifecycle(client, db):
    """TC-LST-05: Owner changes condition/status -> 200 and persists.
    Other student -> 403. Missing/deleted ID -> 404. Reserved listing cannot be made available.
    """
    owner = create_test_user(db, email="update_owner@example.edu")
    other_student = create_test_user(db, email="update_other@example.edu")
    token_owner = create_auth_token(owner)
    token_other = create_auth_token(other_student)
    headers_owner = {"Authorization": f"Bearer {token_owner}"}
    headers_other = {"Authorization": f"Bearer {token_other}"}

    # 1. Seed initial listing: AVAILABLE, GOOD (rank 3)
    listing = create_test_listing(
        db,
        owner=owner,
        title="Operating Systems Principles",
        author="Silberschatz",
        isbn="9781118063330",
        condition_rank=3,
        location="Hostel 4",
        status="AVAILABLE",
    )

    # 2. Owner changes condition to POOR -> 200 and persists
    res_cond = client.put(
        f"/api/v1/listings/{listing.id}",
        headers=headers_owner,
        json={"condition": "POOR"},
    )
    assert res_cond.status_code == 200
    data_cond = res_cond.json()
    assert data_cond["condition"] == "POOR"
    assert data_cond["status"] == "AVAILABLE"
    # Verify in DB
    refreshed_1 = db.query(Listing).filter_by(id=listing.id).one()
    assert refreshed_1.condition_rank == 1

    # 3. Owner changes status to UNAVAILABLE -> 200 and persists
    res_unavail = client.put(
        f"/api/v1/listings/{listing.id}",
        headers=headers_owner,
        json={"status": "UNAVAILABLE"},
    )
    assert res_unavail.status_code == 200
    data_unavail = res_unavail.json()
    assert data_unavail["status"] == "UNAVAILABLE"
    refreshed_2 = db.query(Listing).filter_by(id=listing.id).one()
    assert refreshed_2.status == "UNAVAILABLE"

    # Owner toggles status back to AVAILABLE -> 200 and persists
    res_avail = client.put(
        f"/api/v1/listings/{listing.id}",
        headers=headers_owner,
        json={"status": "AVAILABLE"},
    )
    assert res_avail.status_code == 200
    assert res_avail.json()["status"] == "AVAILABLE"
    refreshed_3 = db.query(Listing).filter_by(id=listing.id).one()
    assert refreshed_3.status == "AVAILABLE"

    # 4. Owner updates location and condition together
    res_multi = client.put(
        f"/api/v1/listings/{listing.id}",
        headers=headers_owner,
        json={"condition": "NEW", "location": "Campus Center Room 101"},
    )
    assert res_multi.status_code == 200
    data_multi = res_multi.json()
    assert data_multi["condition"] == "NEW"
    assert data_multi["location"] == "Campus Center Room 101"

    # 5. Non-owner (other student) attempts to update -> 403
    res_other = client.put(
        f"/api/v1/listings/{listing.id}",
        headers=headers_other,
        json={"condition": "FAIR", "status": "UNAVAILABLE"},
    )
    assert res_other.status_code == 403
    # Listing in DB remains completely unchanged
    refreshed_4 = db.query(Listing).filter_by(id=listing.id).one()
    assert refreshed_4.condition_rank == 4
    assert refreshed_4.status == "AVAILABLE"
    assert refreshed_4.location == "Campus Center Room 101"

    # 6. Missing listing ID -> 404
    res_missing = client.put(
        "/api/v1/listings/999999",
        headers=headers_owner,
        json={"status": "UNAVAILABLE"},
    )
    assert res_missing.status_code == 404

    # 7. Soft-deleted listing ID -> 404
    deleted_listing = create_test_listing(
        db,
        owner=owner,
        title="Deleted Book",
        author="Deleted Author",
        isbn="9780000000999",
        status="AVAILABLE",
        deleted_at=datetime.now(UTC),
    )
    res_deleted = client.put(
        f"/api/v1/listings/{deleted_listing.id}",
        headers=headers_owner,
        json={"status": "UNAVAILABLE"},
    )
    assert res_deleted.status_code == 404

    # 8. Reserved listing cannot be made available -> 409
    reserved_listing = create_test_listing(
        db,
        owner=owner,
        title="Reserved Book",
        author="Reserved Author",
        isbn="9780000000888",
        status="RESERVED",
    )
    res_res_avail = client.put(
        f"/api/v1/listings/{reserved_listing.id}",
        headers=headers_owner,
        json={"status": "AVAILABLE"},
    )
    assert res_res_avail.status_code == 409
    # Verify status in DB remains RESERVED
    res_check = db.query(Listing).filter_by(id=reserved_listing.id).one()
    assert res_check.status == "RESERVED"

    # Reserved listing cannot have book changed -> 409
    res_res_book = client.put(
        f"/api/v1/listings/{reserved_listing.id}",
        headers=headers_owner,
        json={"title": "New Title Attempt"},
    )
    assert res_res_book.status_code == 409
    res_check_b = db.query(Listing).filter_by(id=reserved_listing.id).one()
    assert res_check_b.book.title == "Reserved Book"

    # Reserved listing CAN update condition and location without altering status or book
    res_res_ok = client.put(
        f"/api/v1/listings/{reserved_listing.id}",
        headers=headers_owner,
        json={"condition": "FAIR", "location": "Study Hall 3"},
    )
    assert res_res_ok.status_code == 200
    res_check_c = db.query(Listing).filter_by(id=reserved_listing.id).one()
    assert res_check_c.condition_rank == 2
    assert res_check_c.location == "Study Hall 3"
    assert res_check_c.status == "RESERVED"

    # 9. On-loan listing cannot be made available -> 409
    on_loan_listing = create_test_listing(
        db,
        owner=owner,
        title="On Loan Book",
        author="Loan Author",
        isbn="9780000000777",
        status="ON_LOAN",
    )
    res_loan_avail = client.put(
        f"/api/v1/listings/{on_loan_listing.id}",
        headers=headers_owner,
        json={"status": "AVAILABLE"},
    )
    assert res_loan_avail.status_code == 409

    # On-loan listing cannot have book changed -> 409
    res_loan_book = client.put(
        f"/api/v1/listings/{on_loan_listing.id}",
        headers=headers_owner,
        json={"isbn": "9781111111111"},
    )
    assert res_loan_book.status_code == 409

    # 10. Updating shared book data uses get-or-create ISBN instead of modifying shared catalog
    # Create another listing sharing the same book
    listing_shared_1 = create_test_listing(
        db,
        owner=owner,
        title="Shared Catalog Title",
        author="Shared Catalog Author",
        isbn="9780321125217",
        status="AVAILABLE",
    )
    listing_shared_2 = create_test_listing(
        db,
        owner=other_student,
        title="Shared Catalog Title",
        author="Shared Catalog Author",
        isbn="9780321125217",
        status="AVAILABLE",
    )
    original_book_id = listing_shared_1.book_id
    assert listing_shared_2.book_id == original_book_id

    # Owner updates listing_shared_1 to point to a new ISBN
    res_new_book = client.put(
        f"/api/v1/listings/{listing_shared_1.id}",
        headers=headers_owner,
        json={
            "isbn": "9780134494166",
            "title": "Clean Architecture",
            "author": "Robert C. Martin",
        },
    )
    assert res_new_book.status_code == 200
    data_nb = res_new_book.json()
    assert data_nb["isbn"] == "9780134494166"
    assert data_nb["title"] == "Clean Architecture"

    # Verify listing_shared_2's book is untouched and preserved
    shared_2_refreshed = db.query(Listing).filter_by(id=listing_shared_2.id).one()
    assert shared_2_refreshed.book_id == original_book_id
    assert shared_2_refreshed.book.isbn == "9780321125217"
    assert shared_2_refreshed.book.title == "Shared Catalog Title"


# ==============================================================================
# TC-SEC-05: Server-side ownership and explicit admin role enforcement (SR-005)
# ==============================================================================


def test_tc_sec_05_update_listing_ownership_enforcement(client, db):
    """TC-SEC-05 (SR-005): Student B attempts update/delete of A listing -> 403
    and unchanged data. Test authenticated role/ownership enforcement directly at API.
    Admin user is allowed server-side.
    """
    student_a = create_test_user(db, email="student_sec_a@example.edu")
    student_b = create_test_user(db, email="student_sec_b@example.edu")
    admin_user = create_test_user(db, email="admin_sec@example.edu")
    admin_user.role = "admin"
    db.commit()

    token_b = create_auth_token(student_b)
    token_admin = create_auth_token(admin_user)

    headers_b = {"Authorization": f"Bearer {token_b}"}
    headers_admin = {"Authorization": f"Bearer {token_admin}"}

    # Student A creates listing
    listing_a = create_test_listing(
        db,
        owner=student_a,
        title="Computer Architecture",
        author="Hennessy and Patterson",
        isbn="9780128119051",
        condition_rank=3,
        location="Lab 102",
        status="AVAILABLE",
    )

    # 1. Student B attempts to update Student A's listing directly via API -> 403
    res_hack = client.put(
        f"/api/v1/listings/{listing_a.id}",
        headers=headers_b,
        json={"condition": "POOR", "location": "Hacked Location", "status": "UNAVAILABLE"},
    )
    assert res_hack.status_code == 403

    # Student B attempts to delete Student A's listing directly via API -> 403 (TC-SEC-05)
    res_hack_del = client.delete(
        f"/api/v1/listings/{listing_a.id}",
        headers=headers_b,
    )
    assert res_hack_del.status_code == 403

    # Verify Student A's listing data remains completely unchanged
    persisted = db.query(Listing).filter_by(id=listing_a.id).one()
    assert persisted.condition_rank == 3
    assert persisted.location == "Lab 102"
    assert persisted.status == "AVAILABLE"
    assert persisted.owner_id == student_a.id
    assert persisted.deleted_at is None

    # 2. Unauthenticated caller attempts update or delete -> 401
    res_no_auth = client.put(
        f"/api/v1/listings/{listing_a.id}",
        json={"location": "No Auth Room"},
    )
    assert res_no_auth.status_code == 401

    res_no_auth_del = client.delete(
        f"/api/v1/listings/{listing_a.id}",
    )
    assert res_no_auth_del.status_code == 401

    # 3. Invalid token attempts update or delete -> 401
    res_bad_token = client.put(
        f"/api/v1/listings/{listing_a.id}",
        headers={"Authorization": "Bearer totally_bogus_token"},
        json={"location": "Bad Token Room"},
    )
    assert res_bad_token.status_code == 401

    res_bad_token_del = client.delete(
        f"/api/v1/listings/{listing_a.id}",
        headers={"Authorization": "Bearer totally_bogus_token"},
    )
    assert res_bad_token_del.status_code == 401

    # 4. Admin user performs mutation on Student A's listing -> 200 (SR-005 server-side admin role)
    res_admin = client.put(
        f"/api/v1/listings/{listing_a.id}",
        headers=headers_admin,
        json={"location": "Admin Review Desk", "condition": "NEW"},
    )
    assert res_admin.status_code == 200
    data_admin = res_admin.json()
    assert data_admin["location"] == "Admin Review Desk"
    assert data_admin["condition"] == "NEW"

    # Persisted in database
    persisted_after_admin = db.query(Listing).filter_by(id=listing_a.id).one()
    assert persisted_after_admin.location == "Admin Review Desk"
    assert persisted_after_admin.condition_rank == 4


# ==============================================================================
# Listing mutation: reject protected user fields and validate input.
# ==============================================================================


def test_listing_privilege_escalation_rejected(client, db):
    """Reject protected user fields submitted through listing updates."""
    owner = create_test_user(db, email="priv_escalation@example.edu")
    token = create_auth_token(owner)
    headers = {"Authorization": f"Bearer {token}"}

    listing = create_test_listing(
        db,
        owner=owner,
        title="Database Systems",
        author="Navathe",
        isbn="9780136086208",
        condition_rank=3,
        location="Room 303",
        status="AVAILABLE",
    )

    # 1. Attempt to pass role=admin -> 422
    res_role = client.put(
        f"/api/v1/listings/{listing.id}",
        headers=headers,
        json={"role": "admin"},
    )
    assert res_role.status_code == 422
    refreshed_user = db.query(User).filter_by(id=owner.id).one()
    assert refreshed_user.role == "student"

    # 2. Attempt to pass email -> 422
    res_email = client.put(
        f"/api/v1/listings/{listing.id}",
        headers=headers,
        json={"email": "attacker@example.edu"},
    )
    assert res_email.status_code == 422
    refreshed_user = db.query(User).filter_by(id=owner.id).one()
    assert refreshed_user.email == "priv_escalation@example.edu"

    # 3. Attempt to pass active=False -> 422
    res_active = client.put(
        f"/api/v1/listings/{listing.id}",
        headers=headers,
        json={"active": False},
    )
    assert res_active.status_code == 422
    refreshed_user = db.query(User).filter_by(id=owner.id).one()
    assert refreshed_user.active is True

    # 4. Attempt to pass password_hash -> 422
    res_hash = client.put(
        f"/api/v1/listings/{listing.id}",
        headers=headers,
        json={"password_hash": "malicious_hash_override"},
    )
    assert res_hash.status_code == 422
    refreshed_user = db.query(User).filter_by(id=owner.id).one()
    assert refreshed_user.password_hash == "hashed_pw_test"

    # 5. Attempt to pass owner_id / ownerId -> 422
    res_owner = client.put(
        f"/api/v1/listings/{listing.id}",
        headers=headers,
        json={"owner_id": 999},
    )
    assert res_owner.status_code == 422

    # 6. Field validation: empty string title -> 422
    res_empty_title = client.put(
        f"/api/v1/listings/{listing.id}",
        headers=headers,
        json={"title": "   "},
    )
    assert res_empty_title.status_code == 422

    # 7. Field validation: invalid condition -> 422
    res_bad_cond = client.put(
        f"/api/v1/listings/{listing.id}",
        headers=headers,
        json={"condition": "SUPERB"},
    )
    assert res_bad_cond.status_code == 422

    # 8. Field validation: invalid status (e.g. attempting to jump straight to ON_LOAN) -> 422
    res_bad_status = client.put(
        f"/api/v1/listings/{listing.id}",
        headers=headers,
        json={"status": "ON_LOAN"},
    )
    assert res_bad_status.status_code == 422

    # 9. Field validation: invalid ISBN length -> 422
    res_bad_isbn = client.put(
        f"/api/v1/listings/{listing.id}",
        headers=headers,
        json={"isbn": "12345"},
    )
    assert res_bad_isbn.status_code == 422

    # Verify listing remained completely unchanged through all invalid attempts
    listing_check = db.query(Listing).filter_by(id=listing.id).one()
    assert listing_check.condition_rank == 3
    assert listing_check.location == "Room 303"
    assert listing_check.status == "AVAILABLE"
    assert listing_check.owner_id == owner.id


# ==============================================================================
# TC-LST-06: Owner deletes idle listing, deleted_at set, query exclusion (F-013)
# ==============================================================================


def test_tc_lst_06_delete_idle_listing_and_exclusion(client, db):
    """TC-LST-06: Owner deletes idle listing -> 204, deleted_at set.
    Verify absent in public and mine lists; repeated delete -> 404.
    """
    owner = create_test_user(db, email="delete_owner@example.edu")
    token = create_auth_token(owner)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create idle listing
    listing = create_test_listing(
        db,
        owner=owner,
        title="Modern Operating Systems",
        author="Tanenbaum",
        isbn="9780133591620",
        condition_rank=3,
        location="Hostel 2",
        status="AVAILABLE",
    )

    # Verify listing is present in public search and /listings/mine before deletion
    res_pub_before = client.get(f"/api/v1/listings?isbn={listing.book.isbn}")
    assert res_pub_before.status_code == 200
    assert any(it["id"] == listing.id for it in res_pub_before.json()["items"])

    res_mine_before = client.get("/api/v1/listings/mine", headers=headers)
    assert res_mine_before.status_code == 200
    assert any(it["id"] == listing.id for it in res_mine_before.json()["items"])

    # 2. Owner deletes idle listing -> 204 No Content
    res_del = client.delete(
        f"/api/v1/listings/{listing.id}",
        headers=headers,
    )
    assert res_del.status_code == 204
    assert res_del.content == b""

    # Verify in DB: deleted_at timestamp is now set
    refreshed = db.query(Listing).filter_by(id=listing.id).one()
    assert refreshed.deleted_at is not None

    # 3. Verify absent in public search
    res_pub_after = client.get(f"/api/v1/listings?isbn={listing.book.isbn}")
    assert res_pub_after.status_code == 200
    assert not any(it["id"] == listing.id for it in res_pub_after.json()["items"])

    # 4. Verify absent in owner's /listings/mine
    res_mine_after = client.get("/api/v1/listings/mine", headers=headers)
    assert res_mine_after.status_code == 200
    assert not any(it["id"] == listing.id for it in res_mine_after.json()["items"])

    # 5. Repeated delete on already soft-deleted listing -> 404
    res_repeated_del = client.delete(
        f"/api/v1/listings/{listing.id}",
        headers=headers,
    )
    assert res_repeated_del.status_code == 404

    # 6. Delete on non-existent listing ID -> 404
    res_missing_del = client.delete(
        "/api/v1/listings/999999",
        headers=headers,
    )
    assert res_missing_del.status_code == 404

    # 7. Updating already deleted listing -> 404
    res_update_deleted = client.put(
        f"/api/v1/listings/{listing.id}",
        headers=headers,
        json={"location": "Attempt Update Room"},
    )
    assert res_update_deleted.status_code == 404


# ==============================================================================
# TC-LST-07: Active exchange guard on deletion (F-013 Sprint 1 test double)
# ==============================================================================


def test_tc_lst_07_active_exchange_delete_guard(client, db, monkeypatch):
    """TC-LST-07: Sprint 1: patch has_active_exchange true; deletion -> 409
    and no timestamp change. Sprint 2: create real active exchange and repeat
    without a mock.
    """
    owner = create_test_user(db, email="active_exchange_owner@example.edu")
    token = create_auth_token(owner)
    headers = {"Authorization": f"Bearer {token}"}

    listing = create_test_listing(
        db,
        owner=owner,
        title="Distributed Systems Concepts",
        author="Coulouris",
        isbn="9780132143011",
        condition_rank=4,
        location="Lab 3",
        status="AVAILABLE",
    )

    # 1. Patch has_active_exchange to return True (Sprint 1 test double)
    monkeypatch.setattr(
        "app.routers.listings.has_active_exchange",
        lambda listing_id, db=None: True,
    )

    # 2. Attempt deletion -> 409 Conflict with ACTIVE_EXCHANGE error
    res_del_active = client.delete(
        f"/api/v1/listings/{listing.id}",
        headers=headers,
    )
    assert res_del_active.status_code == 409
    assert "ACTIVE_EXCHANGE" in str(res_del_active.json())

    # 3. Verify in database: deleted_at has NO timestamp change (remains None)
    listing_refreshed = db.query(Listing).filter_by(id=listing.id).one()
    assert listing_refreshed.deleted_at is None

    # Verify listing is still visible in public search and /listings/mine
    res_pub = client.get(f"/api/v1/listings?isbn={listing.book.isbn}")
    assert any(it["id"] == listing.id for it in res_pub.json()["items"])

    res_mine = client.get("/api/v1/listings/mine", headers=headers)
    assert any(it["id"] == listing.id for it in res_mine.json()["items"])

    # 4. Remove patch (has_active_exchange returns False) -> deletion succeeds with 204
    monkeypatch.setattr(
        "app.routers.listings.has_active_exchange",
        lambda listing_id, db=None: False,
    )
    res_del_ok = client.delete(
        f"/api/v1/listings/{listing.id}",
        headers=headers,
    )
    assert res_del_ok.status_code == 204
    listing_deleted = db.query(Listing).filter_by(id=listing.id).one()
    assert listing_deleted.deleted_at is not None
