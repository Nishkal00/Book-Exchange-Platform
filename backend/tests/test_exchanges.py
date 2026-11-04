"""Exchange lifecycle tests: due date, handover, cancellation, history (F-025, TC-EXC-01)."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import Book, BorrowRequest, Exchange, ExchangeEvent, Listing, Match, Notification
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


def future(days=7):
    return (datetime.now(UTC) + timedelta(days=days)).isoformat()


@pytest.fixture
def world(db):
    """A lender, a borrower, an outsider and an ACCEPTED exchange between the first two."""
    lender = create_test_user(db, email="lender@example.edu")
    borrower = create_test_user(db, email="borrower@example.edu")
    outsider = create_test_user(db, email="outsider@example.edu")
    book = Book(isbn="9780131103627", title="The C Programming Language", author="K&R")
    db.add(book)
    db.flush()
    listing = Listing(
        owner_id=lender.id, book_id=book.id, condition_rank=1, location="Campus", status="RESERVED"
    )
    request = BorrowRequest(
        borrower_id=borrower.id, isbn="9780131103627", location="Campus", status="FULFILLED"
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
        match_id=match.id, request_id=request.id, listing_id=listing.id, state="ACCEPTED"
    )
    db.add(exchange)
    db.commit()
    return {
        "lender": lender,
        "borrower": borrower,
        "outsider": outsider,
        "listing": listing,
        "request": request,
        "exchange": exchange,
    }


def test_participant_can_view_exchange_and_outsider_cannot(client, world):
    url = f"/api/v1/exchanges/{world['exchange'].id}"
    assert client.get(url, headers=auth(world["borrower"])).status_code == 200
    assert client.get(url, headers=auth(world["lender"])).status_code == 200
    assert client.get(url, headers=auth(world["outsider"])).status_code == 404
    assert client.get(url).status_code in (401, 403)


def test_either_participant_sets_future_due_date(client, world, db):
    url = f"/api/v1/exchanges/{world['exchange'].id}/due-date"
    for user in (world["borrower"], world["lender"]):
        response = client.put(url, json={"due_at": future()}, headers=auth(user))
        assert response.status_code == 200
        assert response.json()["due_at"] is not None
        assert response.json()["state"] == "ACCEPTED"
    events = db.query(ExchangeEvent).filter_by(event_type="DUE_DATE_SET").count()
    assert events == 2


def test_due_date_must_be_in_the_future(client, world):
    url = f"/api/v1/exchanges/{world['exchange'].id}/due-date"
    past = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    response = client.put(url, json={"due_at": past}, headers=auth(world["lender"]))
    assert response.status_code == 422
    assert response.json()["detail"] == "DUE_DATE_NOT_IN_FUTURE"


def test_outsider_cannot_set_due_date(client, world):
    url = f"/api/v1/exchanges/{world['exchange'].id}/due-date"
    response = client.put(url, json={"due_at": future()}, headers=auth(world["outsider"]))
    assert response.status_code == 404


def test_handover_requires_due_date(client, world):
    url = f"/api/v1/exchanges/{world['exchange'].id}/handover"
    response = client.post(url, headers=auth(world["lender"]))
    assert response.status_code == 409
    assert response.json()["detail"] == "DUE_DATE_REQUIRED"


def test_only_lender_can_confirm_handover(client, world):
    base = f"/api/v1/exchanges/{world['exchange'].id}"
    client.put(f"{base}/due-date", json={"due_at": future()}, headers=auth(world["lender"]))
    response = client.post(f"{base}/handover", headers=auth(world["borrower"]))
    assert response.status_code == 403
    assert response.json()["detail"] == "LENDER_ONLY"
    assert client.post(f"{base}/handover", headers=auth(world["outsider"])).status_code == 404


def test_lender_handover_moves_to_on_loan(client, world, db):
    base = f"/api/v1/exchanges/{world['exchange'].id}"
    client.put(f"{base}/due-date", json={"due_at": future()}, headers=auth(world["borrower"]))
    response = client.post(f"{base}/handover", headers=auth(world["lender"]))
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "ON_LOAN"
    assert body["handover_confirmed_at"] is not None
    assert [e["event_type"] for e in body["events"]] == ["DUE_DATE_SET", "HANDOVER_CONFIRMED"]
    db.refresh(world["listing"])
    assert world["listing"].status == "ON_LOAN"
    notes = db.query(Notification).filter_by(event_type="EXCHANGE_UPDATED").all()
    assert len([n for n in notes if n.event_key.endswith("ON_LOAN")]) == 2


def test_handover_twice_is_rejected(client, world):
    base = f"/api/v1/exchanges/{world['exchange'].id}"
    client.put(f"{base}/due-date", json={"due_at": future()}, headers=auth(world["lender"]))
    assert client.post(f"{base}/handover", headers=auth(world["lender"])).status_code == 200
    again = client.post(f"{base}/handover", headers=auth(world["lender"]))
    assert again.status_code == 409
    assert again.json()["detail"] == "INVALID_EXCHANGE_STATE"


@pytest.mark.parametrize("who", ["borrower", "lender"])
def test_either_participant_can_cancel_before_handover(client, world, db, who):
    base = f"/api/v1/exchanges/{world['exchange'].id}"
    response = client.post(f"{base}/cancel", headers=auth(world[who]))
    assert response.status_code == 200
    assert response.json()["state"] == "CANCELLED"
    assert response.json()["cancelled_at"] is not None
    db.refresh(world["listing"])
    db.refresh(world["request"])
    assert world["listing"].status == "AVAILABLE"
    assert world["request"].status == "OPEN"
    last = response.json()["events"][-1]
    assert (last["from_state"], last["to_state"], last["actor_id"]) == (
        "ACCEPTED",
        "CANCELLED",
        world[who].id,
    )


def test_cancel_after_handover_is_rejected(client, world, db):
    base = f"/api/v1/exchanges/{world['exchange'].id}"
    client.put(f"{base}/due-date", json={"due_at": future()}, headers=auth(world["lender"]))
    client.post(f"{base}/handover", headers=auth(world["lender"]))
    for who in ("borrower", "lender"):
        response = client.post(f"{base}/cancel", headers=auth(world[who]))
        assert response.status_code == 409
        assert response.json()["detail"] == "CANCEL_AFTER_HANDOVER"
    db.refresh(world["exchange"])
    assert world["exchange"].state == "ON_LOAN"


def test_outsider_cannot_cancel(client, world):
    url = f"/api/v1/exchanges/{world['exchange'].id}/cancel"
    assert client.post(url, headers=auth(world["outsider"])).status_code == 404


def test_cannot_change_due_date_after_cancel(client, world):
    base = f"/api/v1/exchanges/{world['exchange'].id}"
    client.post(f"{base}/cancel", headers=auth(world["lender"]))
    response = client.put(
        f"{base}/due-date", json={"due_at": future()}, headers=auth(world["lender"])
    )
    assert response.status_code == 409


def test_exchange_history_returns_borrower_and_lender_records(client, world):
    borrower_response = client.get(
        "/api/v1/exchanges",
        headers=auth(world["borrower"]),
    )
    lender_response = client.get(
        "/api/v1/exchanges",
        headers=auth(world["lender"]),
    )

    assert borrower_response.status_code == 200
    assert lender_response.status_code == 200

    borrower_body = borrower_response.json()
    lender_body = lender_response.json()

    assert borrower_body["total"] == 1
    assert lender_body["total"] == 1

    borrower_item = borrower_body["items"][0]
    lender_item = lender_body["items"][0]

    assert borrower_item["partner_id"] == world["lender"].id
    assert borrower_item["partner_display_name"] == world["lender"].name

    assert lender_item["partner_id"] == world["borrower"].id
    assert lender_item["partner_display_name"] == world["borrower"].name


def test_exchange_history_does_not_expose_other_students_exchanges(client, world):
    response = client.get(
        "/api/v1/exchanges",
        headers=auth(world["outsider"]),
    )

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total"] == 0


def test_exchange_history_includes_book_dates_and_state(client, world):
    response = client.get(
        "/api/v1/exchanges",
        headers=auth(world["borrower"]),
    )

    assert response.status_code == 200

    item = response.json()["items"][0]

    assert item["id"] == world["exchange"].id
    assert item["book_title"] == "The C Programming Language"
    assert item["book_author"] == "K&R"
    assert item["state"] == "ACCEPTED"
    assert item["created_at"] is not None
    assert item["due_at"] is None
    assert item["handover_confirmed_at"] is None
    assert item["returned_at"] is None
    assert item["cancelled_at"] is None


def test_exchange_history_supports_pagination(client, world, db):
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
        state="ACCEPTED",
    )
    db.add(second_exchange)
    db.commit()

    first_page = client.get(
        "/api/v1/exchanges?limit=1&offset=0",
        headers=auth(world["borrower"]),
    )
    second_page = client.get(
        "/api/v1/exchanges?limit=1&offset=1",
        headers=auth(world["borrower"]),
    )

    assert first_page.status_code == 200
    assert second_page.status_code == 200
    assert first_page.json()["total"] == 2
    assert second_page.json()["total"] == 2
    assert len(first_page.json()["items"]) == 1
    assert len(second_page.json()["items"]) == 1

    assert first_page.json()["items"][0]["id"] != second_page.json()["items"][0]["id"]


def test_exchange_history_rejects_invalid_pagination(client, world):
    headers = auth(world["borrower"])

    assert (
        client.get(
            "/api/v1/exchanges?limit=0",
            headers=headers,
        ).status_code
        == 422
    )

    assert (
        client.get(
            "/api/v1/exchanges?limit=101",
            headers=headers,
        ).status_code
        == 422
    )

    assert (
        client.get(
            "/api/v1/exchanges?offset=-1",
            headers=headers,
        ).status_code
        == 422
    )


def test_exchange_history_requires_authentication(client):
    response = client.get("/api/v1/exchanges")
    assert response.status_code in (401, 403)


def test_contact_visible_to_both_exchange_participants(client, world):
    url = f"/api/v1/exchanges/{world['exchange'].id}/contact"

    borrower_response = client.get(url, headers=auth(world["borrower"]))
    lender_response = client.get(url, headers=auth(world["lender"]))

    assert borrower_response.status_code == 200
    assert borrower_response.json()["email"] == world["lender"].email

    assert lender_response.status_code == 200
    assert lender_response.json()["email"] == world["borrower"].email


def test_outsider_cannot_view_partner_contact(client, world):
    url = f"/api/v1/exchanges/{world['exchange'].id}/contact"

    response = client.get(url, headers=auth(world["outsider"]))

    assert response.status_code == 403


def test_contact_hidden_until_mutual_acceptance(client, world, db):
    match = db.query(Match).filter_by(id=world["exchange"].match_id).first()
    match.lender_accepted = False
    db.commit()

    url = f"/api/v1/exchanges/{world['exchange'].id}/contact"
    response = client.get(url, headers=auth(world["borrower"]))

    assert response.status_code == 403


def test_cancelled_exchange_revokes_contact_access(client, world, db):
    world["exchange"].state = "CANCELLED"
    db.commit()

    url = f"/api/v1/exchanges/{world['exchange'].id}/contact"
    response = client.get(url, headers=auth(world["borrower"]))

    assert response.status_code == 403
