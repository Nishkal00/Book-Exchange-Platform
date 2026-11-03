"""Exchanges router: due date, handover and cancellation (F-025, TC-EXC-01)."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Exchange, ExchangeEvent, User
from app.routers.auth import get_current_user
from app.services.notifications import create_notification

router = APIRouter(prefix="/api/v1/exchanges", tags=["exchanges"])


class DueDatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    due_at: datetime


class ExchangeEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_id: int
    event_type: str
    from_state: str | None
    to_state: str
    created_at: datetime


class ExchangeOut(BaseModel):
    id: int
    request_id: int
    listing_id: int
    borrower_id: int
    lender_id: int
    state: str
    due_at: datetime | None
    handover_confirmed_at: datetime | None
    cancelled_at: datetime | None
    events: list[ExchangeEventOut]


def _load_exchange(db: Session, exchange_id: int, user: User) -> Exchange:
    """Return the exchange only to its participants; others get 404 (no existence leak)."""
    exchange = db.execute(
        select(Exchange).where(Exchange.id == exchange_id).with_for_update()
    ).scalar_one_or_none()
    if exchange is None or user.id not in (
        exchange.request.borrower_id,
        exchange.listing.owner_id,
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EXCHANGE_NOT_FOUND")
    return exchange


def _record(db: Session, exchange: Exchange, actor: User, event_type: str, to_state: str) -> None:
    db.add(
        ExchangeEvent(
            exchange_id=exchange.id,
            actor_id=actor.id,
            event_type=event_type,
            from_state=exchange.state,
            to_state=to_state,
        )
    )


def _notify(db: Session, exchange: Exchange, state: str, message: str) -> None:
    for user_id in (exchange.request.borrower_id, exchange.listing.owner_id):
        create_notification(
            db,
            user_id=user_id,
            event_key=f"exchange:{exchange.id}:state:{state}",
            event_type="EXCHANGE_UPDATED",
            message=message,
        )


def _serialize(db: Session, exchange: Exchange) -> ExchangeOut:
    events = (
        db.execute(
            select(ExchangeEvent)
            .where(ExchangeEvent.exchange_id == exchange.id)
            .order_by(ExchangeEvent.created_at, ExchangeEvent.id)
        )
        .scalars()
        .all()
    )
    return ExchangeOut(
        id=exchange.id,
        request_id=exchange.request_id,
        listing_id=exchange.listing_id,
        borrower_id=exchange.request.borrower_id,
        lender_id=exchange.listing.owner_id,
        state=exchange.state,
        due_at=exchange.due_at,
        handover_confirmed_at=exchange.handover_confirmed_at,
        cancelled_at=exchange.cancelled_at,
        events=[ExchangeEventOut.model_validate(e) for e in events],
    )


def _require_state(exchange: Exchange, *allowed: str) -> None:
    if exchange.state not in allowed:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="INVALID_EXCHANGE_STATE")


@router.get("/{exchange_id}", response_model=ExchangeOut)
def get_exchange(
    exchange_id: int,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> ExchangeOut:
    exchange = _load_exchange(db, exchange_id, current_user)
    return _serialize(db, exchange)


@router.put("/{exchange_id}/due-date", response_model=ExchangeOut)
def set_due_date(
    exchange_id: int,
    payload: DueDatePayload,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> ExchangeOut:
    """Record the agreed future due date for an ACCEPTED exchange (either participant)."""
    exchange = _load_exchange(db, exchange_id, current_user)
    _require_state(exchange, "ACCEPTED")

    due_at = payload.due_at
    if due_at.tzinfo is None:
        due_at = due_at.replace(tzinfo=UTC)
    if due_at <= datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="DUE_DATE_NOT_IN_FUTURE"
        )

    exchange.due_at = due_at
    _record(db, exchange, current_user, "DUE_DATE_SET", exchange.state)
    db.commit()
    return _serialize(db, exchange)


@router.post("/{exchange_id}/handover", response_model=ExchangeOut)
def confirm_handover(
    exchange_id: int,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> ExchangeOut:
    """Lender confirms handover: ACCEPTED -> ON_LOAN (requires an agreed due date)."""
    exchange = _load_exchange(db, exchange_id, current_user)
    if current_user.id != exchange.listing.owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="LENDER_ONLY")
    _require_state(exchange, "ACCEPTED")
    if exchange.due_at is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="DUE_DATE_REQUIRED")

    _record(db, exchange, current_user, "HANDOVER_CONFIRMED", "ON_LOAN")
    exchange.state = "ON_LOAN"
    exchange.handover_confirmed_at = datetime.now(UTC)
    exchange.listing.status = "ON_LOAN"
    _notify(
        db,
        exchange,
        "ON_LOAN",
        f"'{exchange.listing.book.title}' has been handed over and is now on loan.",
    )
    db.commit()
    return _serialize(db, exchange)


@router.post("/{exchange_id}/cancel", response_model=ExchangeOut)
def cancel_exchange(
    exchange_id: int,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> ExchangeOut:
    """Either participant may cancel before handover; cancelling after handover is rejected."""
    exchange = _load_exchange(db, exchange_id, current_user)
    if exchange.state == "ON_LOAN":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="CANCEL_AFTER_HANDOVER")
    _require_state(exchange, "ACCEPTED")

    _record(db, exchange, current_user, "CANCELLED", "CANCELLED")
    exchange.state = "CANCELLED"
    exchange.cancelled_at = datetime.now(UTC)
    exchange.listing.status = "AVAILABLE"
    exchange.request.status = "OPEN"
    _notify(
        db,
        exchange,
        "CANCELLED",
        f"The exchange for '{exchange.listing.book.title}' was cancelled before handover.",
    )
    db.commit()
    return _serialize(db, exchange)
