"""Requests router: create, cancel, and get ranked matches (SRS F-020, F-021, F-022, SAD 4.3.1)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, computed_field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import BorrowRequest, Exchange, User
from app.routers.auth import get_current_user
from app.routers.listings import ListingOut, serialize_listing
from app.services.matching import recompute_matches_for_request

router = APIRouter(prefix="/api/v1/requests", tags=["requests"])


class CreateBorrowRequestPayload(BaseModel):
    """Payload schema for creating a borrow request (F-020)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    isbn: str | None = None
    query: str | None = None
    location: str = Field(min_length=1, max_length=100)


class BorrowRequestOut(BaseModel):
    """Public schema for a borrow request (SAD 4.3.1)."""

    id: int
    borrower_id: int
    isbn: str | None
    query: str | None
    location: str
    status: str
    created_at: datetime

    @computed_field
    @property
    def borrowerId(self) -> int:
        return self.borrower_id

    @computed_field
    @property
    def createdAt(self) -> datetime:
        return self.created_at


class MatchSuggestionOut(BaseModel):
    """Ranked match suggestion schema for borrower (SAD 4.3.1 / F-022)."""

    match_id: int
    listing: ListingOut
    score: float
    state: str

    @computed_field
    @property
    def matchId(self) -> int:
        return self.match_id


def serialize_request(req: BorrowRequest) -> BorrowRequestOut:
    """Helper to convert BorrowRequest to BorrowRequestOut."""
    return BorrowRequestOut(
        id=req.id,
        borrower_id=req.borrower_id,
        isbn=req.isbn,
        query=req.query,
        location=req.location,
        status=req.status,
        created_at=req.created_at,
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=BorrowRequestOut)
def create_borrow_request(
    payload: CreateBorrowRequestPayload,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> BorrowRequestOut:
    """Create an OPEN borrow request specifying ISBN or a nonempty query and location (F-020).

    Rejects duplicate active requests by the same student with identical criteria with 409.
    """
    clean_isbn = payload.isbn.replace("-", "").strip() if payload.isbn else None
    clean_query = payload.query.strip() if payload.query else None

    if not clean_isbn and not clean_query:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Either ISBN or title/author query must be provided",
        )

    if clean_isbn:
        if not (len(clean_isbn) in (10, 13) and clean_isbn.isdigit()):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="ISBN must be 10 or 13 digits after hyphen removal",
            )

    clean_location = payload.location.strip()
    if not clean_location:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Location cannot be empty",
        )

    # Check for duplicate active requests by the same student and criteria (F-020)
    existing_active = (
        db.query(BorrowRequest)
        .filter(
            BorrowRequest.borrower_id == current_user.id,
            BorrowRequest.status.in_(["OPEN", "MATCHED"]),
            BorrowRequest.isbn == clean_isbn,
            BorrowRequest.query == clean_query,
            BorrowRequest.location == clean_location,
        )
        .first()
    )
    if existing_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="DUPLICATE_ACTIVE_REQUEST",
        )

    new_request = BorrowRequest(
        borrower_id=current_user.id,
        isbn=clean_isbn,
        query=clean_query,
        location=clean_location,
        status="OPEN",
    )
    db.add(new_request)
    db.commit()
    db.refresh(new_request)

    return serialize_request(new_request)


@router.post("/{request_id}/cancel", response_model=BorrowRequestOut)
def cancel_borrow_request(
    request_id: int,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> BorrowRequestOut:
    """Allow only the borrower to cancel an OPEN or MATCHED request (F-021).

    Releases uncommitted reservations and invalidates linked pending matches atomically.
    An active exchange returns 409 Conflict.
    Repeat cancel on an already cancelled request is idempotent (200).
    """
    req = db.query(BorrowRequest).filter(BorrowRequest.id == request_id).first()
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Borrow request not found",
        )

    if req.borrower_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to cancel this request",
        )

    if req.status == "CANCELLED":
        return serialize_request(req)

    # Check if involved in an active exchange
    active_exchange = (
        db.query(Exchange)
        .filter(
            Exchange.request_id == req.id,
            Exchange.state.in_(["ACCEPTED", "ON_LOAN"]),
        )
        .first()
    )
    if active_exchange:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="ACTIVE_EXCHANGE",
        )

    req.status = "CANCELLED"

    # Invalidate linked proposed matches
    for m in req.matches:
        if m.status == "PROPOSED":
            m.status = "EXPIRED"

    db.commit()
    db.refresh(req)
    return serialize_request(req)


@router.get("/{request_id}/matches", response_model=list[MatchSuggestionOut])
def get_request_matches(
    request_id: int,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> list[MatchSuggestionOut]:
    """Return top 5 deterministic ranked suggestions for borrower (F-022, TC-MAT-01, TC-MAT-03).

    Excludes own, deleted, inactive, and active-exchange offers.
    Recomputed on each call to reflect latest listing and match statuses.
    Omits partner contact details (SR-007).
    """
    req = db.query(BorrowRequest).filter(BorrowRequest.id == request_id).first()
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Borrow request not found",
        )

    if req.borrower_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the borrower can view match suggestions",
        )

    # Recompute matches dynamically
    matches = recompute_matches_for_request(db, req)

    suggestions = [
        MatchSuggestionOut(
            match_id=m.id,
            listing=serialize_listing(m.listing),
            score=float(m.score),
            state=m.status,
        )
        for m in matches
    ]
    return suggestions
