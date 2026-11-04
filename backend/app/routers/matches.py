"""Matches router: participant decisions and mutual acceptance (F-022, F-024, SAD 4.3.1)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import BorrowRequest, Listing, Match, User
from app.routers.auth import get_current_user
from app.services.matching import handle_match_decision

router = APIRouter(prefix="/api/v1/matches", tags=["matches"])


class MatchDecisionPayload(BaseModel):
    """Payload schema for match decision (SAD 4.3.1)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    decision: str


class MatchDecisionResponse(BaseModel):
    """Response schema for match decision (SAD 4.3.1)."""

    status: str
    borrowerAccepted: bool
    lenderAccepted: bool
    exchangeId: int | None = None


@router.post("/{match_id}/decision", response_model=MatchDecisionResponse)
def submit_match_decision(
    match_id: int,
    payload: MatchDecisionPayload,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> MatchDecisionResponse:
    """Submit accept or decline decision for a proposed match (F-022, F-024, TC-MAT-02).

    Only participant (borrower or lender) may submit.
    Mutual acceptance atomically reserves the listing and creates an active exchange.
    Competing acceptances fail with 409 Conflict.
    Declining recomputes matches for the request.
    """
    result = handle_match_decision(
        db=db,
        match_id=match_id,
        current_user_id=current_user.id,
        decision=payload.decision,
    )
    return MatchDecisionResponse(
        status=result["status"],
        borrowerAccepted=result["borrowerAccepted"],
        lenderAccepted=result["lenderAccepted"],
        exchangeId=result["exchangeId"],
    )


class MatchListItem(BaseModel):
    """A match the current user takes part in, without any contact details (SR-007)."""

    match_id: int
    request_id: int
    listing_id: int
    role: str
    status: str
    score: float
    title: str
    author: str
    isbn: str
    location: str
    my_decision: bool
    partner_decision: bool
    exchange_id: int | None = None


@router.get("", response_model=list[MatchListItem])
def list_my_matches(
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> list[MatchListItem]:
    """List matches where the user is the borrower or the lender (F-022, F-024).

    Expired matches are left out. No partner identity or contact details are returned;
    those are disclosed only after mutual acceptance through the exchange (SR-007).
    """
    matches = (
        db.execute(
            select(Match)
            .join(BorrowRequest, Match.request_id == BorrowRequest.id)
            .join(Listing, Match.listing_id == Listing.id)
            .options(
                joinedload(Match.request),
                joinedload(Match.listing).joinedload(Listing.book),
                joinedload(Match.exchange),
            )
            .where(
                (BorrowRequest.borrower_id == current_user.id)
                | (Listing.owner_id == current_user.id),
                Match.status != "EXPIRED",
            )
            .order_by(Match.created_at.desc(), Match.id.desc())
        )
        .scalars()
        .unique()
        .all()
    )

    items = []
    for match in matches:
        is_borrower = match.request.borrower_id == current_user.id
        items.append(
            MatchListItem(
                match_id=match.id,
                request_id=match.request_id,
                listing_id=match.listing_id,
                role="borrower" if is_borrower else "lender",
                status=match.status,
                score=float(match.score),
                title=match.listing.book.title,
                author=match.listing.book.author,
                isbn=match.listing.book.isbn,
                location=match.listing.location,
                my_decision=match.borrower_accepted if is_borrower else match.lender_accepted,
                partner_decision=match.lender_accepted if is_borrower else match.borrower_accepted,
                exchange_id=match.exchange.id if match.exchange else None,
            )
        )
    return items
