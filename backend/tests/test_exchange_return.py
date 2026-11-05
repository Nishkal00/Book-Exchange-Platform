"""Confirm return tests (F-026, TC-EXC-02)."""

import pytest

from app.models import ExchangeEvent, Notification
from tests.test_exchanges import auth, client, future, world  # noqa: F401


@pytest.fixture
def on_loan(client, world):  # noqa: F811
    base = f"/api/v1/exchanges/{world['exchange'].id}"
    client.put(f"{base}/due-date", json={"due_at": future()}, headers=auth(world["lender"]))
    assert client.post(f"{base}/handover", headers=auth(world["lender"])).status_code == 200
    return base


def events(db, event_type):
    return db.query(ExchangeEvent).filter_by(event_type=event_type).count()


def test_first_confirmation_keeps_exchange_on_loan(client, world, db, on_loan):  # noqa: F811
    response = client.post(f"{on_loan}/return", headers=auth(world["borrower"]))
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "ON_LOAN"
    assert body["borrower_return_confirmed"] is True
    assert body["lender_return_confirmed"] is False
    assert body["returned_at"] is None
    db.refresh(world["listing"])
    assert world["listing"].status == "ON_LOAN"
    assert events(db, "RETURN_CONFIRMED") == 1
    assert events(db, "RETURNED") == 0


def test_second_confirmation_returns_exchange_and_frees_listing(client, world, db, on_loan):  # noqa: F811
    client.post(f"{on_loan}/return", headers=auth(world["borrower"]))
    response = client.post(f"{on_loan}/return", headers=auth(world["lender"]))
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "RETURNED"
    assert body["borrower_return_confirmed"] is True
    assert body["lender_return_confirmed"] is True
    assert body["returned_at"] is not None
    db.refresh(world["listing"])
    db.refresh(world["exchange"])
    assert world["listing"].status == "AVAILABLE"
    assert world["exchange"].returned_at is not None
    assert events(db, "RETURNED") == 1
    assert body["events"][-1]["to_state"] == "RETURNED"


def test_lender_can_confirm_first(client, world, db, on_loan):  # noqa: F811
    assert (
        client.post(f"{on_loan}/return", headers=auth(world["lender"])).json()["state"] == "ON_LOAN"
    )
    assert (
        client.post(f"{on_loan}/return", headers=auth(world["borrower"])).json()["state"]
        == "RETURNED"
    )


def test_repeated_confirmation_is_idempotent(client, world, db, on_loan):  # noqa: F811
    for _ in range(3):
        assert client.post(f"{on_loan}/return", headers=auth(world["borrower"])).status_code == 200
    assert events(db, "RETURN_CONFIRMED") == 1
    notes = db.query(Notification).filter(Notification.event_key.like("%:return:%")).count()
    assert notes == 1

    client.post(f"{on_loan}/return", headers=auth(world["lender"]))
    for who in ("borrower", "lender", "borrower"):
        response = client.post(f"{on_loan}/return", headers=auth(world[who]))
        assert response.status_code == 200
        assert response.json()["state"] == "RETURNED"
    assert events(db, "RETURN_CONFIRMED") == 2
    assert events(db, "RETURNED") == 1
    returned_notes = (
        db.query(Notification).filter(Notification.event_key.like("%:state:RETURNED")).count()
    )
    assert returned_notes == 2


def test_partner_is_notified_after_first_confirmation(client, world, db, on_loan):  # noqa: F811
    client.post(f"{on_loan}/return", headers=auth(world["borrower"]))
    note = db.query(Notification).filter(Notification.event_key.like("%:return:%")).one()
    assert note.user_id == world["lender"].id
    assert "Please confirm" in note.message


def test_cannot_confirm_return_before_handover(client, world):  # noqa: F811
    url = f"/api/v1/exchanges/{world['exchange'].id}/return"
    response = client.post(url, headers=auth(world["borrower"]))
    assert response.status_code == 409
    assert response.json()["detail"] == "INVALID_EXCHANGE_STATE"


def test_cannot_confirm_return_after_cancel(client, world):  # noqa: F811
    base = f"/api/v1/exchanges/{world['exchange'].id}"
    client.post(f"{base}/cancel", headers=auth(world["lender"]))
    assert client.post(f"{base}/return", headers=auth(world["borrower"])).status_code == 409


def test_outsider_and_anonymous_cannot_confirm_return(client, world, on_loan):  # noqa: F811
    assert client.post(f"{on_loan}/return", headers=auth(world["outsider"])).status_code == 404
    assert client.post(f"{on_loan}/return").status_code in (401, 403)


def test_returned_listing_can_be_lent_again(client, world, db, on_loan):  # noqa: F811
    client.post(f"{on_loan}/return", headers=auth(world["borrower"]))
    client.post(f"{on_loan}/return", headers=auth(world["lender"]))
    db.refresh(world["listing"])
    assert world["listing"].status == "AVAILABLE"
