"""Exchanges router: history, contact disclosure, due date, handover, cancellation and ratings."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, computed_field
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import BorrowRequest, Exchange, ExchangeEvent, Listing, Rating, User
from app.routers.auth import get_current_user
from app.services.notifications import create_notification

router = APIRouter(prefix="/api/v1/exchanges", tags=["exchanges"])


# ---------------------------------------------------------------------------
# Request and response schemas
# ---------------------------------------------------------------------------


class DueDatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    due_at: datetime


class RatingPayload(BaseModel):
    """Request body for submitting an exchange-partner rating."""

    model_config = ConfigDict(extra="forbid")

    rating: int = Field(strict=True, ge=1, le=5)


class RatingOut(BaseModel):
    """Accepted rating and the recipient's updated average."""

    id: int
    exchange_id: int
    rater_id: int
    ratee_id: int
    rating: int
    created_at: datetime
    recipient_avg_rating: float


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
    """Partner contact details disclosed only to exchange participants."""

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
    """Legacy exchange history response retained for API compatibility."""

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


class ExchangeHistoryItem(ExchangeHistoryOut):
    """Expanded exchange history item returned by the paginated endpoint."""

    book_author: str
    partner_display_name: str
    handover_confirmed_at: datetime | None = None
    returned_at: datetime | None = None
    cancelled_at: datetime | None = None


class ExchangeHistoryResponse(BaseModel):
    """Paginated exchange history response."""

    items: list[ExchangeHistoryItem]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _load_exchange(db: Session, exchange_id: int, user: User) -> Exchange:
    """Load an exchange only if the requesting user is a participant."""

    exchange = db.execute(
        select(Exchange).where(Exchange.id == exchange_id).with_for_update()
    ).scalar_one_or_none()

    if exchange is None or user.id not in (
        exchange.request.borrower_id,
        exchange.listing.owner_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="EXCHANGE_NOT_FOUND",
        )

    return exchange


def _record(
    db: Session,
    exchange: Exchange,
    actor: User,
    event_type: str,
    to_state: str,
) -> None:
    """Record an exchange state-transition event."""

    db.add(
        ExchangeEvent(
            exchange_id=exchange.id,
            actor_id=actor.id,
            event_type=event_type,
            from_state=exchange.state,
            to_state=to_state,
        )
    )


def _notify(
    db: Session,
    exchange: Exchange,
    state: str,
    message: str,
) -> None:
    """Notify both exchange participants."""

    for user_id in (
        exchange.request.borrower_id,
        exchange.listing.owner_id,
    ):
        create_notification(
            db,
            user_id=user_id,
            event_key=f"exchange:{exchange.id}:state:{state}",
            event_type="EXCHANGE_UPDATED",
            message=message,
        )


def _serialize(db: Session, exchange: Exchange) -> ExchangeOut:
    """Serialize an exchange with its event history."""

    events = (
        db.execute(
            select(ExchangeEvent)
            .where(ExchangeEvent.exchange_id == exchange.id)
            .order_by(
                ExchangeEvent.created_at,
                ExchangeEvent.id,
            )
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
        events=[ExchangeEventOut.model_validate(event) for event in events],
    )


def _require_state(exchange: Exchange, *allowed: str) -> None:
    """Reject operations that are invalid for the current exchange state."""

    if exchange.state not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="INVALID_EXCHANGE_STATE",
        )


# ---------------------------------------------------------------------------
# F-030: Exchange history
# ---------------------------------------------------------------------------


@router.get("", response_model=ExchangeHistoryResponse)
def get_my_exchanges(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> ExchangeHistoryResponse:
    """Return paginated exchange history for the authenticated participant."""

    if not 1 <= limit <= 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="LIMIT_MUST_BE_BETWEEN_1_AND_100",
        )

    if offset < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="OFFSET_MUST_BE_NON_NEGATIVE",
        )

    participant_filter = or_(
        Exchange.request.has(BorrowRequest.borrower_id == current_user.id),
        Exchange.listing.has(Listing.owner_id == current_user.id),
    )

    total = db.query(func.count(Exchange.id)).filter(participant_filter).scalar() or 0

    exchanges = (
        db.query(Exchange)
        .filter(participant_filter)
        .options(
            joinedload(Exchange.request).joinedload(BorrowRequest.borrower),
            joinedload(Exchange.listing).joinedload(Listing.owner),
            joinedload(Exchange.listing).joinedload(Listing.book),
        )
        .order_by(
            Exchange.created_at.desc(),
            Exchange.id.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = []

    for exchange in exchanges:
        borrower = exchange.request.borrower
        lender = exchange.listing.owner
        book = exchange.listing.book

        if current_user.id == borrower.id:
            partner = lender
            role = "borrower"
        elif current_user.id == lender.id:
            partner = borrower
            role = "lender"
        else:
            continue

        items.append(
            ExchangeHistoryItem(
                id=exchange.id,
                match_id=exchange.match_id,
                request_id=exchange.request_id,
                listing_id=exchange.listing_id,
                state=exchange.state,
                partner_id=partner.id,
                partner_name=partner.name,
                role=role,
                book_title=book.title,
                book_author=book.author,
                partner_display_name=partner.name,
                created_at=exchange.created_at,
                due_at=exchange.due_at,
                handover_confirmed_at=exchange.handover_confirmed_at,
                returned_at=exchange.returned_at,
                cancelled_at=exchange.cancelled_at,
            )
        )

    return ExchangeHistoryResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


# ---------------------------------------------------------------------------
# Exchange details
# ---------------------------------------------------------------------------


@router.get("/{exchange_id}", response_model=ExchangeOut)
def get_exchange(
    exchange_id: int,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> ExchangeOut:
    """Return exchange details to one of its participants."""

    exchange = _load_exchange(db, exchange_id, current_user)
    return _serialize(db, exchange)


# ---------------------------------------------------------------------------
# F-024: Partner contact disclosure
# ---------------------------------------------------------------------------


@router.get(
    "/{exchange_id}/contact",
    response_model=PartnerContactOut,
)
def get_exchange_partner_contact(
    exchange_id: int,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> PartnerContactOut:
    """
    Disclose partner contact details only to exchange participants.

    Non-participants receive 403.
    Cancelled exchanges revoke contact access.
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


# ---------------------------------------------------------------------------
# F-025: Due date
# ---------------------------------------------------------------------------


@router.put(
    "/{exchange_id}/due-date",
    response_model=ExchangeOut,
)
def set_due_date(
    exchange_id: int,
    payload: DueDatePayload,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> ExchangeOut:
    """Record the agreed future due date for an ACCEPTED exchange."""

    exchange = _load_exchange(db, exchange_id, current_user)
    _require_state(exchange, "ACCEPTED")

    due_at = payload.due_at

    if due_at.tzinfo is None:
        due_at = due_at.replace(tzinfo=UTC)

    if due_at <= datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="DUE_DATE_NOT_IN_FUTURE",
        )

    exchange.due_at = due_at

    _record(
        db,
        exchange,
        current_user,
        "DUE_DATE_SET",
        exchange.state,
    )

    db.commit()

    return _serialize(db, exchange)


# ---------------------------------------------------------------------------
# F-025: Handover
# ---------------------------------------------------------------------------


@router.post(
    "/{exchange_id}/handover",
    response_model=ExchangeOut,
)
def confirm_handover(
    exchange_id: int,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> ExchangeOut:
    """Lender confirms handover: ACCEPTED -> ON_LOAN."""

    exchange = _load_exchange(db, exchange_id, current_user)

    if current_user.id != exchange.listing.owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="LENDER_ONLY",
        )

    _require_state(exchange, "ACCEPTED")

    if exchange.due_at is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="DUE_DATE_REQUIRED",
        )

    _record(
        db,
        exchange,
        current_user,
        "HANDOVER_CONFIRMED",
        "ON_LOAN",
    )

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


# ---------------------------------------------------------------------------
# F-025: Cancellation
# ---------------------------------------------------------------------------


@router.post(
    "/{exchange_id}/cancel",
    response_model=ExchangeOut,
)
def cancel_exchange(
    exchange_id: int,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> ExchangeOut:
    """Either participant may cancel before handover."""

    exchange = _load_exchange(db, exchange_id, current_user)

    if exchange.state == "ON_LOAN":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="CANCEL_AFTER_HANDOVER",
        )

    _require_state(exchange, "ACCEPTED")

    _record(
        db,
        exchange,
        current_user,
        "CANCELLED",
        "CANCELLED",
    )

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


# ---------------------------------------------------------------------------
# F-026: Confirm return
# ---------------------------------------------------------------------------


@router.post(
    "/{exchange_id}/return",
    response_model=ExchangeOut,
)
def confirm_return(
    exchange_id: int,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> ExchangeOut:
    """Record the caller's return confirmation (TC-EXC-02).

    The exchange moves ON_LOAN -> RETURNED only once both the borrower and the lender have
    confirmed, and the listing then becomes AVAILABLE again. Confirming twice is idempotent:
    no extra event, notification or state change.
    """

    exchange = _load_exchange(db, exchange_id, current_user)
    is_borrower = current_user.id == exchange.request.borrower_id

    # A returned exchange stays as it is, whoever calls again.
    if exchange.state == "RETURNED":
        return _serialize(db, exchange)

    _require_state(exchange, "ON_LOAN")

    already_confirmed = (
        exchange.borrower_return_confirmed if is_borrower else exchange.lender_return_confirmed
    )
    if already_confirmed:
        return _serialize(db, exchange)

    if is_borrower:
        exchange.borrower_return_confirmed = True
    else:
        exchange.lender_return_confirmed = True

    _record(db, exchange, current_user, "RETURN_CONFIRMED", exchange.state)

    title = exchange.listing.book.title

    if exchange.borrower_return_confirmed and exchange.lender_return_confirmed:
        _record(db, exchange, current_user, "RETURNED", "RETURNED")
        exchange.state = "RETURNED"
        exchange.returned_at = datetime.now(UTC)
        exchange.listing.status = "AVAILABLE"
        _notify(
            db,
            exchange,
            "RETURNED",
            f"'{title}' has been returned. The exchange is complete.",
        )
    else:
        partner_id = exchange.listing.owner_id if is_borrower else exchange.request.borrower_id
        create_notification(
            db,
            user_id=partner_id,
            event_key=f"exchange:{exchange.id}:return:{current_user.id}",
            event_type="EXCHANGE_UPDATED",
            message=f"Your partner confirmed the return of '{title}'. Please confirm it too.",
        )

    db.commit()

    return _serialize(db, exchange)


# ---------------------------------------------------------------------------
# F-031: Ratings
# ---------------------------------------------------------------------------


@router.post(
    "/{exchange_id}/ratings",
    response_model=RatingOut,
    status_code=status.HTTP_201_CREATED,
)
def submit_rating(
    exchange_id: int,
    payload: RatingPayload,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> RatingOut:
    """Allow each exchange participant to rate their partner once after return."""

    exchange = _load_exchange(db, exchange_id, current_user)
    _require_state(exchange, "RETURNED")

    borrower_id = exchange.request.borrower_id
    lender_id = exchange.listing.owner_id

    if current_user.id == borrower_id:
        ratee_id = lender_id
    elif current_user.id == lender_id:
        ratee_id = borrower_id
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="NOT_AN_EXCHANGE_PARTICIPANT",
        )

    if current_user.id == ratee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SELF_RATING_NOT_ALLOWED",
        )

    existing_rating = db.execute(
        select(Rating).where(
            Rating.exchange_id == exchange_id,
            Rating.rater_id == current_user.id,
        )
    ).scalar_one_or_none()

    if existing_rating is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="RATING_ALREADY_SUBMITTED",
        )

    new_rating = Rating(
        exchange_id=exchange_id,
        rater_id=current_user.id,
        ratee_id=ratee_id,
        rating=payload.rating,
    )
    db.add(new_rating)

    try:
        # Flush first so the new rating is included in the aggregate query.
        db.flush()

        average_rating = db.execute(
            select(func.avg(Rating.rating)).where(Rating.ratee_id == ratee_id)
        ).scalar_one()

        recipient = db.get(User, ratee_id)
        if recipient is None:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="RATING_RECIPIENT_NOT_FOUND",
            )

        recipient.avg_rating = average_rating
        db.commit()
        db.refresh(new_rating)

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="RATING_ALREADY_SUBMITTED",
        ) from None

    return RatingOut(
        id=new_rating.id,
        exchange_id=new_rating.exchange_id,
        rater_id=new_rating.rater_id,
        ratee_id=new_rating.ratee_id,
        rating=new_rating.rating,
        created_at=new_rating.created_at,
        recipient_avg_rating=float(recipient.avg_rating),
    )
