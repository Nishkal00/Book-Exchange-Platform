"""Matching engine with scoring, locking, and re-match (SAD 3.5.1 / F-022)."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models import BorrowRequest, Exchange, Listing, Match, User


def trigrams(s: str) -> set[str]:
    """Generate 3-character trigrams with pg_trgm standard padding (2 spaces before, 1 after)."""
    padded = f"  {s.lower()} "
    return {padded[i : i + 3] for i in range(len(padded) - 2)}


def calculate_trigram_similarity(s1: str, s2: str) -> float:
    """Calculate Jaccard trigram similarity matching PostgreSQL pg_trgm.

    Returns float in [0.0, 1.0].
    """
    if not s1 or not s2:
        return 0.0
    t1 = trigrams(s1)
    t2 = trigrams(s2)
    union = len(t1 | t2)
    if union == 0:
        return 0.0
    return round(len(t1 & t2) / union, 4)


def calculate_match_score(
    request_isbn: str | None,
    request_query: str | None,
    request_location: str,
    listing_isbn: str,
    listing_title: str,
    listing_author: str,
    listing_condition_rank: int,
    listing_location: str,
) -> tuple[float, float] | None:
    """Compute deterministic match score and relevance according to SAD 3.5.1.

    Score = 70*relevance + 20*same_location + 10*(condition_rank/4).
    Relevance is 1.0 for exact ISBN or title trigram similarity in [0, 1] for text requests.
    Returns (score, relevance) if candidate matches, or None if candidate does not match.
    """
    req_isbn_norm = request_isbn.replace("-", "").strip() if request_isbn else None
    list_isbn_norm = listing_isbn.replace("-", "").strip() if listing_isbn else None

    is_match = False
    relevance = 0.0

    if req_isbn_norm:
        if req_isbn_norm == list_isbn_norm:
            relevance = 1.0
            is_match = True
        else:
            return None

    if not is_match and request_query:
        q = request_query.strip().lower()
        t = listing_title.strip().lower()
        a = listing_author.strip().lower()

        sim = calculate_trigram_similarity(q, t)
        containment = (q in t) or (q in a)

        if containment or sim >= 0.3:
            is_match = True
            relevance = sim

    if not is_match:
        return None

    same_loc = (
        1.0
        if (
            request_location
            and listing_location
            and request_location.strip().lower() == listing_location.strip().lower()
        )
        else 0.0
    )

    condition_factor = listing_condition_rank / 4.0
    score = 70.0 * relevance + 20.0 * same_loc + 10.0 * condition_factor
    return round(score, 2), round(relevance, 4)


def get_candidate_listings(
    db: Session, request: BorrowRequest
) -> list[tuple[Listing, float, float]]:
    """Query and rank available, non-deleted listings from active users.

    Exclusions applied:
    - Soft-deleted listings (deleted_at IS NOT NULL)
    - Unavailable listings (status != 'AVAILABLE')
    - Borrower's own listings (owner_id == request.borrower_id)
    - Inactive owners (owner.active IS FALSE)
    - Listings currently involved in an active exchange (ACCEPTED, ON_LOAN)
    - Listings previously DECLINED or EXPIRED for this specific request

    Returns list of (Listing, score, relevance) sorted deterministically:
    descending score, newest listing (created_at DESC), then listing ID ASC.
    Capped at top 5 candidates.
    """
    # 1. Subquery/set for listings involved in active exchanges
    active_exchange_listing_ids = {
        row[0]
        for row in db.query(Exchange.listing_id)
        .filter(Exchange.state.in_(["ACCEPTED", "ON_LOAN"]))
        .all()
    }

    # 2. Set for listings declined or expired for this specific request
    excluded_match_listing_ids = {
        row[0]
        for row in db.query(Match.listing_id)
        .filter(
            Match.request_id == request.id,
            Match.status.in_(["DECLINED", "EXPIRED"]),
        )
        .all()
    }

    # 3. Base query for eligible listings
    query = (
        db.query(Listing)
        .options(joinedload(Listing.book), joinedload(Listing.owner))
        .join(User, Listing.owner_id == User.id)
        .filter(
            Listing.deleted_at.is_(None),
            Listing.status == "AVAILABLE",
            Listing.owner_id != request.borrower_id,
            User.active.is_(True),
        )
    )

    if active_exchange_listing_ids:
        query = query.filter(Listing.id.notin_(active_exchange_listing_ids))
    if excluded_match_listing_ids:
        query = query.filter(Listing.id.notin_(excluded_match_listing_ids))

    all_listings = query.all()

    candidates: list[tuple[Listing, float, float]] = []
    for lst in all_listings:
        scored = calculate_match_score(
            request_isbn=request.isbn,
            request_query=request.query,
            request_location=request.location,
            listing_isbn=lst.book.isbn,
            listing_title=lst.book.title,
            listing_author=lst.book.author,
            listing_condition_rank=lst.condition_rank,
            listing_location=lst.location,
        )
        if scored is not None:
            score, relevance = scored
            candidates.append((lst, score, relevance))

    # Sort descending score, then newest listing (created_at DESC), then listing ID ASC
    def sort_key(item: tuple[Listing, float, float]) -> tuple[float, float, int]:
        listing, score, _ = item
        created_ts = listing.created_at.timestamp() if listing.created_at else 0.0
        return (-score, -created_ts, listing.id)

    candidates.sort(key=sort_key)
    return candidates[:5]


def recompute_matches_for_request(db: Session, request: BorrowRequest) -> list[Match]:
    """Recompute proposed matches for a request after decline, status change, or new offers.

    Deterministic suggestions capped at top 5.
    Obsolete suggestions (no longer in top 5 or listing no longer eligible) are marked EXPIRED.
    Updates request status to MATCHED if suggestions exist, or OPEN if none exist.
    """
    candidates = get_candidate_listings(db, request)
    top_listing_ids = {lst.id for lst, _, _ in candidates}

    # Fetch existing matches for this request
    existing_matches = (
        db.query(Match)
        .options(joinedload(Match.listing).joinedload(Listing.book))
        .filter(Match.request_id == request.id)
        .all()
    )
    existing_by_listing = {m.listing_id: m for m in existing_matches}

    # Mark previously proposed matches that fell out of the top 5 as EXPIRED
    for m in existing_matches:
        if m.status == "PROPOSED" and m.listing_id not in top_listing_ids:
            m.status = "EXPIRED"

    result_matches: list[Match] = []
    for lst, score, relevance in candidates:
        if lst.id in existing_by_listing:
            match = existing_by_listing[lst.id]
            match.score = score
            match.relevance = relevance
            if match.status == "EXPIRED":
                match.status = "PROPOSED"
                match.borrower_accepted = False
                match.lender_accepted = False
        else:
            match = Match(
                request_id=request.id,
                listing_id=lst.id,
                score=score,
                relevance=relevance,
                status="PROPOSED",
                borrower_accepted=False,
                lender_accepted=False,
            )
            db.add(match)
            db.flush()
        result_matches.append(match)

    if result_matches:
        if request.status == "OPEN":
            request.status = "MATCHED"
    else:
        if request.status == "MATCHED":
            request.status = "OPEN"

    db.commit()

    # Re-order result matches to strictly reflect candidate ranking
    match_dict = {m.listing_id: m for m in result_matches}
    ordered_matches = [match_dict[lst.id] for lst, _, _ in candidates if lst.id in match_dict]
    return ordered_matches


def handle_match_decision(
    db: Session, match_id: int, current_user_id: int, decision: str
) -> dict[str, Any]:
    """Process participant accept or decline decision with transaction locking (SAD 3.5.1 / 4.2).

    Only mutual acceptance creates an active exchange and reserves the listing.
    Rejects competing acceptances with 409 Conflict.
    Re-matches on decline.
    """
    decision_clean = decision.strip().lower()
    if decision_clean not in ("accept", "decline"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Decision must be 'accept' or 'decline'",
        )

    match = (
        db.query(Match)
        .options(
            joinedload(Match.request),
            joinedload(Match.listing),
        )
        .filter(Match.id == match_id)
        .first()
    )
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found",
        )

    is_borrower = match.request.borrower_id == current_user_id
    is_lender = match.listing.owner_id == current_user_id

    if not (is_borrower or is_lender):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a participant of this match",
        )

    # 1. Decline decision
    if decision_clean == "decline":
        if match.status in ("ACCEPTED", "EXPIRED"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot decline accepted or expired match",
            )
        match.status = "DECLINED"
        db.commit()

        # Recompute matches for the request so another listing can be suggested
        recompute_matches_for_request(db, match.request)
        return {
            "status": "DECLINED",
            "borrowerAccepted": match.borrower_accepted,
            "lenderAccepted": match.lender_accepted,
            "exchangeId": None,
        }

    # 2. Accept decision
    if match.status in ("DECLINED", "EXPIRED"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="STALE_MATCH",
        )

    # Check if participant already accepted (idempotent / repeat decision is safe)
    if is_borrower and match.borrower_accepted and not match.lender_accepted:
        return {
            "status": match.status,
            "borrowerAccepted": match.borrower_accepted,
            "lenderAccepted": match.lender_accepted,
            "exchangeId": match.exchange.id if match.exchange else None,
        }
    if is_lender and match.lender_accepted and not match.borrower_accepted:
        return {
            "status": match.status,
            "borrowerAccepted": match.borrower_accepted,
            "lenderAccepted": match.lender_accepted,
            "exchangeId": match.exchange.id if match.exchange else None,
        }

    if is_borrower:
        match.borrower_accepted = True
    if is_lender:
        match.lender_accepted = True

    # If only one participant accepted so far
    if not (match.borrower_accepted and match.lender_accepted):
        db.commit()
        return {
            "status": match.status,
            "borrowerAccepted": match.borrower_accepted,
            "lenderAccepted": match.lender_accepted,
            "exchangeId": None,
        }

    # Both accepted: mutual acceptance transition!
    # Lock and recheck listing and request eligibility
    listing = db.query(Listing).filter(Listing.id == match.listing_id).first()
    request = db.query(BorrowRequest).filter(BorrowRequest.id == match.request_id).first()

    # Verify listing is still available and not soft-deleted
    if not listing or listing.status != "AVAILABLE" or listing.deleted_at is not None:
        match.status = "EXPIRED"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="LISTING_NOT_AVAILABLE",
        )

    # Verify listing is not in another active exchange
    existing_active = (
        db.query(Exchange)
        .filter(
            Exchange.listing_id == match.listing_id,
            Exchange.state.in_(["ACCEPTED", "ON_LOAN"]),
        )
        .first()
    )
    if existing_active:
        match.status = "EXPIRED"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="LISTING_ALREADY_RESERVED",
        )

    # Verify request is not already fulfilled
    if not request or request.status in ("FULFILLED", "CANCELLED"):
        match.status = "EXPIRED"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="REQUEST_NOT_ACTIVE",
        )

    # Create Exchange and update states in one atomic transaction
    exchange = Exchange(
        match_id=match.id,
        request_id=match.request_id,
        listing_id=match.listing_id,
        state="ACCEPTED",
    )
    db.add(exchange)
    listing.status = "RESERVED"
    request.status = "FULFILLED"
    match.status = "ACCEPTED"

    try:
        db.commit()
        db.refresh(exchange)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="LISTING_ALREADY_RESERVED",
        ) from None

    # Invalidate conflicting pending matches for this listing or request
    conflicting = (
        db.query(Match)
        .filter(
            (Match.listing_id == match.listing_id) | (Match.request_id == match.request_id),
            Match.id != match.id,
            Match.status == "PROPOSED",
        )
        .all()
    )
    for cm in conflicting:
        cm.status = "EXPIRED"
    db.commit()

    return {
        "status": "ACCEPTED",
        "borrowerAccepted": True,
        "lenderAccepted": True,
        "exchangeId": exchange.id,
    }
