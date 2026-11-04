"""Requests router: create, cancel, and get ranked matches (F-020, F-021, F-022)."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import BorrowRequest, Exchange, User
from app.routers.auth import get_current_user
from app.routers.listings import ListingOut, serialize_listing
from app.services.matching import recompute_matches_for_request

router = APIRouter(prefix="/api/v1/requests", tags=["requests"])


class CreateBorrowRequestPayload(BaseModel):
    """Payload for creating a borrow request (F-020)."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    isbn: str | None = Field(default=None, min_length=10, max_length=17)
    query: str | None = Field(default=None, min_length=1, max_length=200)
    title_query: str | None = Field(default=None, min_length=1, max_length=200)
    location: str = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_criterion(self):
        if self.query is not None and self.title_query is not None:
            raise ValueError("Provide only one of query or title_query")

        if self.title_query is not None:
            self.query = self.title_query

        if bool(self.isbn) == bool(self.query):
            raise ValueError("Provide exactly one of isbn or title_query")

        if self.isbn is not None:
            normalized = self.isbn.replace("-", "").replace(" ", "")
            if len(normalized) not in (10, 13) or not normalized.isdigit():
                raise ValueError("ISBN must contain 10 or 13 digits")
            self.isbn = normalized

        if self.query is not None:
            self.query = self.query.strip()
            if not self.query:
                raise ValueError("Title query cannot be empty")

        return self


class BorrowRequestOut(BaseModel):
    """Public schema for a borrow request."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    borrower_id: int
    isbn: str | None
    query: str | None
    title_query: str | None = None
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
    """Ranked match suggestion schema for a borrower."""

    match_id: int
    listing: ListingOut
    score: float
    state: str

    @computed_field
    @property
    def matchId(self) -> int:
        return self.match_id


def serialize_request(req: BorrowRequest) -> BorrowRequestOut:
    """Convert a BorrowRequest ORM instance to its response schema."""
    return BorrowRequestOut(
        id=req.id,
        borrower_id=req.borrower_id,
        isbn=req.isbn,
        query=req.query,
        title_query=req.query,
        location=req.location,
        status=req.status,
        created_at=req.created_at,
    )


@router.get("", response_model=list[BorrowRequestOut])
def list_my_borrow_requests(
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> list[BorrowRequestOut]:
    """List the authenticated user's own borrow requests, newest first (F-020, F-021)."""

    requests_ = db.scalars(
        select(BorrowRequest)
        .where(BorrowRequest.borrower_id == current_user.id)
        .order_by(BorrowRequest.created_at.desc(), BorrowRequest.id.desc())
    ).all()
    return [serialize_request(req) for req in requests_]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=BorrowRequestOut)
def create_borrow_request(
    payload: CreateBorrowRequestPayload,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> BorrowRequestOut:
    """Create an OPEN request using an ISBN or query and a location."""

    clean_isbn = payload.isbn
    clean_query = payload.query.strip() if payload.query else None
    clean_location = payload.location.strip()

    if not clean_location:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Location cannot be empty",
        )

    criteria = [
        BorrowRequest.borrower_id == current_user.id,
        BorrowRequest.status.in_(["OPEN", "MATCHED"]),
    ]

    if clean_isbn is not None:
        criteria.append(BorrowRequest.isbn == clean_isbn)
    else:
        criteria.append(BorrowRequest.query == clean_query)

    existing = db.scalar(select(BorrowRequest).where(*criteria))

    if existing is not None:
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
    """Cancel an owned OPEN or MATCHED request atomically."""

    req = db.query(BorrowRequest).filter(BorrowRequest.id == request_id).with_for_update().first()

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

    if req.status not in ("OPEN", "MATCHED"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Request cannot be cancelled in its current status",
        )

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

    try:
        req.status = "CANCELLED"

        for match in req.matches:
            if match.status == "PROPOSED":
                match.status = "EXPIRED"

        db.commit()
        db.refresh(req)
    except Exception:
        db.rollback()
        raise

    return serialize_request(req)


@router.get("/{request_id}/matches", response_model=list[MatchSuggestionOut])
def get_request_matches(
    request_id: int,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> list[MatchSuggestionOut]:
    """Return ranked suggestions for the authenticated borrower."""

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

    matches = recompute_matches_for_request(db, req)

    return [
        MatchSuggestionOut(
            match_id=match.id,
            listing=serialize_listing(match.listing),
            score=float(match.score),
            state=match.status,
        )
        for match in matches
    ]
