"""GET /api/v1/matches lists a user's matches for both roles without contact details."""

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import Book, BorrowRequest, Listing, Match
from tests.test_listings import create_auth_token, create_test_user


@pytest.fixture
def client(db):
    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def auth(user):
    return {"Authorization": f"Bearer {create_auth_token(user)}"}


@pytest.fixture
def world(db):
    lender = create_test_user(db, email="lender@example.edu")
    borrower = create_test_user(db, email="borrower@example.edu")
    outsider = create_test_user(db, email="outsider@example.edu")
    book = Book(isbn="9780131103627", title="The C Programming Language", author="K&R")
    db.add(book)
    db.flush()
    listing = Listing(owner_id=lender.id, book_id=book.id, condition_rank=1, location="Campus")
    request = BorrowRequest(borrower_id=borrower.id, isbn=book.isbn, location="Campus")
    db.add_all([listing, request])
    db.flush()
    match = Match(
        request_id=request.id,
        listing_id=listing.id,
        score=88,
        borrower_accepted=True,
        lender_accepted=False,
    )
    expired = Match(request_id=request.id, listing_id=listing.id, score=10, status="EXPIRED")
    db.add_all([match, expired])
    db.commit()
    return {"lender": lender, "borrower": borrower, "outsider": outsider, "match": match}


def test_borrower_sees_own_match_with_decisions(client, world):
    data = client.get("/api/v1/matches", headers=auth(world["borrower"])).json()
    assert len(data) == 1
    item = data[0]
    assert item["role"] == "borrower"
    assert item["title"] == "The C Programming Language"
    assert (item["my_decision"], item["partner_decision"]) == (True, False)
    assert item["status"] == "PROPOSED"
    assert item["exchange_id"] is None


def test_lender_sees_match_with_swapped_decisions(client, world):
    item = client.get("/api/v1/matches", headers=auth(world["lender"])).json()[0]
    assert item["role"] == "lender"
    assert (item["my_decision"], item["partner_decision"]) == (False, True)


def test_outsider_sees_nothing_and_no_contact_fields_leak(client, world):
    assert client.get("/api/v1/matches", headers=auth(world["outsider"])).json() == []
    item = client.get("/api/v1/matches", headers=auth(world["lender"])).json()[0]
    assert not {"email", "phone", "borrower_id", "owner_id"} & set(item)


def test_requires_login(client):
    assert client.get("/api/v1/matches").status_code in (401, 403)
