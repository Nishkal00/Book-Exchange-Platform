"""Exchanges router: history, contact disclosure, due date, handover (F-024, F-025, SR-007)."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, computed_field
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import BorrowRequest, Exchange, ExchangeEvent, Listing, User
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

    @computed_field
    @property
    def cancelledAt(self) -> datetime | None:
        return self.cancelled_at


class PartnerContactOut(BaseModel):
    """Partner contact details disclosed ONLY after mutual acceptance (SR-007 / F-024)."""

    user_id: int
    name: str
    email: str
    department: str | None = None
    location: str

    @computed_field
    @property
    def userId(self) -> int:
        return self.user_id


class ExchangeHistoryOut(BaseModel):
    """Exchange history item for participant (SAD 4.3.1 / F-030)."""

    id: int
    match_id: int
    request_id: int
    listing_id: int
    state: str
    partner_id: int
    partner_name: str
    role: str
    book_title: str
    due_at: datetime | None = None
    created_at: datetime

    @computed_field
    @property
    def matchId(self) -> int:
        return self.match_id

    @computed_field
    @property
    def requestId(self) -> int:
        return self.request_id

    @computed_field
    @property
    def listingId(self) -> int:
        return self.listing_id

    @computed_field
    @property
    def partnerId(self) -> int:
        return self.partner_id

    @computed_field
    @property
    def partnerName(self) -> str:
        return self.partner_name

    @computed_field
    @property
    def bookTitle(self) -> str:
        return self.book_title

    @computed_field
    @property
    def dueAt(self) -> datetime | None:
        return self.due_at

    @computed_field
    @property
    def createdAt(self) -> datetime:
        return self.created_at


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


@router.get("", response_model=list[ExchangeHistoryOut])
def get_my_exchanges(
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> list[ExchangeHistoryOut]:
    """Return paginated/list exchange history for authenticated participant (SAD 4.3.1).

    Omits private contact information in list view (SR-007).
    """
    exchanges = (
        db.query(Exchange)
        .join(Exchange.request)
        .join(Exchange.listing)
        .filter(
            (BorrowRequest.borrower_id == current_user.id) | (Listing.owner_id == current_user.id)
        )
        .options(
            joinedload(Exchange.request).joinedload(BorrowRequest.borrower),
            joinedload(Exchange.listing).joinedload(Listing.owner),
            joinedload(Exchange.listing).joinedload(Listing.book),
        )
        .order_by(Exchange.created_at.desc())
        .all()
    )

    my_exchanges: list[ExchangeHistoryOut] = []
    for ex in exchanges:
        borrower = ex.request.borrower
        lender = ex.listing.owner
        if current_user.id == borrower.id:
            my_exchanges.append(
                ExchangeHistoryOut(
                    id=ex.id,
                    match_id=ex.match_id,
                    request_id=ex.request_id,
                    listing_id=ex.listing_id,
                    state=ex.state,
                    partner_id=lender.id,
                    partner_name=lender.name,
                    role="borrower",
                    book_title=ex.listing.book.title,
                    due_at=ex.due_at,
                    created_at=ex.created_at,
                )
            )
        elif current_user.id == lender.id:
            my_exchanges.append(
                ExchangeHistoryOut(
                    id=ex.id,
                    match_id=ex.match_id,
                    request_id=ex.request_id,
                    listing_id=ex.listing_id,
                    state=ex.state,
                    partner_id=borrower.id,
                    partner_name=borrower.name,
                    role="lender",
                    book_title=ex.listing.book.title,
                    due_at=ex.due_at,
                    created_at=ex.created_at,
                )
            )

    return my_exchanges


@router.get("/{exchange_id}", response_model=ExchangeOut)
def get_exchange(
    exchange_id: int,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> ExchangeOut:
    exchange = _load_exchange(db, exchange_id, current_user)
    return _serialize(db, exchange)


@router.get("/{exchange_id}/contact", response_model=PartnerContactOut)
def get_exchange_partner_contact(
    exchange_id: int,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> PartnerContactOut:
    """Disclose partner contact details ONLY after mutual acceptance (F-024, SR-007, TC-SEC-07).

    - Non-participants receive 403 Forbidden.
    - Cancelled exchanges lose contact access (403 Forbidden).
    - Unmutually accepted or non-existent exchanges return 404.
    """
    exchange = (
        db.query(Exchange)
        .options(
            joinedload(Exchange.request).joinedload(BorrowRequest.borrower),
            joinedload(Exchange.listing).joinedload(Listing.owner),
        )
        .filter(Exchange.id == exchange_id)
        .first()
    )

    if not exchange:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exchange not found",
        )

    borrower = exchange.request.borrower
    lender = exchange.listing.owner

    is_borrower = current_user.id == borrower.id
    is_lender = current_user.id == lender.id

    if not (is_borrower or is_lender):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view contact for this exchange",
        )

    # SR-007 / TC-SEC-07: Cancellation revokes contact access
    if exchange.state == "CANCELLED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Contact access revoked for cancelled exchange",
        )

    partner = lender if is_borrower else borrower

    return PartnerContactOut(
        user_id=partner.id,
        name=partner.name,
        email=partner.email,
        department=partner.department,
        location=partner.location,
    )


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
