"""Ratings tests: partner ratings after returned exchanges (F-031, TC-RAT-01)."""

import pytest

from app.models import Rating
from tests import test_exchanges
from tests.test_exchanges import auth, future


@pytest.fixture
def client(db):
    yield from test_exchanges.client.__wrapped__(db)


@pytest.fixture
def world(db):
    return test_exchanges.world.__wrapped__(db)


@pytest.fixture
def returned_exchange(client, world):
    """Create an exchange that has completed the return workflow."""

    base = f"/api/v1/exchanges/{world['exchange'].id}"

    # Set due date.
    due_response = client.put(
        f"{base}/due-date",
        json={"due_at": future()},
        headers=auth(world["lender"]),
    )
    assert due_response.status_code == 200

    # Lender confirms handover.
    handover_response = client.post(
        f"{base}/handover",
        headers=auth(world["lender"]),
    )
    assert handover_response.status_code == 200
    assert handover_response.json()["state"] == "ON_LOAN"

    # Borrower confirms return.
    borrower_return = client.post(
        f"{base}/return",
        headers=auth(world["borrower"]),
    )
    assert borrower_return.status_code == 200
    assert borrower_return.json()["state"] == "ON_LOAN"

    # Lender confirms return.
    lender_return = client.post(
        f"{base}/return",
        headers=auth(world["lender"]),
    )
    assert lender_return.status_code == 200
    assert lender_return.json()["state"] == "RETURNED"

    return f"{base}/ratings"


def test_borrower_can_rate_lender(client, world, db, returned_exchange):
    """TC-RAT-01: Borrower can rate the lender after return."""

    response = client.post(
        returned_exchange,
        json={"rating": 5},
        headers=auth(world["borrower"]),
    )

    assert response.status_code == 201

    body = response.json()

    assert body["exchange_id"] == world["exchange"].id
    assert body["rater_id"] == world["borrower"].id
    assert body["ratee_id"] == world["lender"].id
    assert body["rating"] == 5
    assert body["recipient_avg_rating"] == 5.0

    db.refresh(world["lender"])
    assert float(world["lender"].avg_rating) == 5.0

    assert db.query(Rating).count() == 1


def test_lender_can_rate_borrower(client, world, db, returned_exchange):
    """Lender can independently rate the borrower."""

    response = client.post(
        returned_exchange,
        json={"rating": 4},
        headers=auth(world["lender"]),
    )

    assert response.status_code == 201

    body = response.json()

    assert body["rater_id"] == world["lender"].id
    assert body["ratee_id"] == world["borrower"].id
    assert body["rating"] == 4
    assert body["recipient_avg_rating"] == 4.0

    db.refresh(world["borrower"])
    assert float(world["borrower"].avg_rating) == 4.0


def test_both_participants_can_rate_same_exchange(client, world, db, returned_exchange):
    """Both participants can submit one rating each."""

    borrower_response = client.post(
        returned_exchange,
        json={"rating": 5},
        headers=auth(world["borrower"]),
    )

    lender_response = client.post(
        returned_exchange,
        json={"rating": 3},
        headers=auth(world["lender"]),
    )

    assert borrower_response.status_code == 201
    assert lender_response.status_code == 201

    assert db.query(Rating).count() == 2

    db.refresh(world["lender"])
    db.refresh(world["borrower"])

    assert float(world["lender"].avg_rating) == 5.0
    assert float(world["borrower"].avg_rating) == 3.0


def test_rating_before_return_is_rejected(client, world):
    """Ratings cannot be submitted while an exchange is ACCEPTED."""

    url = f"/api/v1/exchanges/{world['exchange'].id}/ratings"

    response = client.post(
        url,
        json={"rating": 5},
        headers=auth(world["borrower"]),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "INVALID_EXCHANGE_STATE"


def test_duplicate_rating_is_rejected(client, world, db, returned_exchange):
    """A participant cannot rate the same exchange twice."""

    first_response = client.post(
        returned_exchange,
        json={"rating": 5},
        headers=auth(world["borrower"]),
    )

    second_response = client.post(
        returned_exchange,
        json={"rating": 4},
        headers=auth(world["borrower"]),
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json()["detail"] == "RATING_ALREADY_SUBMITTED"

    assert db.query(Rating).count() == 1


@pytest.mark.parametrize("rating", [0, 6, -1, 10])
def test_rating_outside_valid_range_is_rejected(client, world, returned_exchange, rating):
    """Only ratings between 1 and 5 are accepted."""

    response = client.post(
        returned_exchange,
        json={"rating": rating},
        headers=auth(world["borrower"]),
    )

    assert response.status_code == 422


@pytest.mark.parametrize("rating", [1.5, "5", True, None])
def test_non_integer_rating_is_rejected(client, world, returned_exchange, rating):
    """Rating must be a strict integer."""

    response = client.post(
        returned_exchange,
        json={"rating": rating},
        headers=auth(world["borrower"]),
    )

    assert response.status_code == 422


def test_outsider_cannot_submit_rating(client, world, returned_exchange):
    """Users outside the exchange cannot submit ratings."""

    response = client.post(
        returned_exchange,
        json={"rating": 5},
        headers=auth(world["outsider"]),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "EXCHANGE_NOT_FOUND"


def test_anonymous_user_cannot_submit_rating(client, returned_exchange):
    """Rating submission requires authentication."""

    response = client.post(
        returned_exchange,
        json={"rating": 5},
    )

    assert response.status_code in (401, 403)


def test_recipient_average_is_recalculated_across_exchanges(client, world, db, returned_exchange):
    """Recipient average includes all accepted ratings."""

    first_response = client.post(
        returned_exchange,
        json={"rating": 5},
        headers=auth(world["borrower"]),
    )

    assert first_response.status_code == 201
    assert first_response.json()["recipient_avg_rating"] == 5.0

    # Create a second exchange involving the same lender and borrower.
    from app.models import Book, BorrowRequest, Exchange, Listing, Match

    second_book = Book(
        isbn="9780132350884",
        title="Clean Code",
        author="Robert C. Martin",
    )
    db.add(second_book)
    db.flush()

    second_listing = Listing(
        owner_id=world["lender"].id,
        book_id=second_book.id,
        condition_rank=1,
        location="Campus",
        status="RESERVED",
    )

    second_request = BorrowRequest(
        borrower_id=world["borrower"].id,
        isbn="9780132350884",
        location="Campus",
        status="FULFILLED",
    )

    db.add_all([second_listing, second_request])
    db.flush()

    second_match = Match(
        request_id=second_request.id,
        listing_id=second_listing.id,
        score=85,
        borrower_accepted=True,
        lender_accepted=True,
        status="ACCEPTED",
    )

    db.add(second_match)
    db.flush()

    second_exchange = Exchange(
        match_id=second_match.id,
        request_id=second_request.id,
        listing_id=second_listing.id,
        state="RETURNED",
    )

    db.add(second_exchange)
    db.commit()

    second_url = f"/api/v1/exchanges/{second_exchange.id}/ratings"

    second_response = client.post(
        second_url,
        json={"rating": 3},
        headers=auth(world["borrower"]),
    )

    assert second_response.status_code == 201
    assert second_response.json()["recipient_avg_rating"] == 4.0

    db.refresh(world["lender"])
    assert float(world["lender"].avg_rating) == 4.0
