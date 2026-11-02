"""Matches router: participant decisions and mutual acceptance (F-022, F-024, SAD 4.3.1)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
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
