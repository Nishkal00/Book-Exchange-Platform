from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuditEvent, Exchange, Listing, User
from app.routers.auth import get_current_admin

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


class ModerationRequest(BaseModel):
    """Reason supplied by an administrator for a moderation action."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    reason: str = Field(min_length=1, max_length=1000)


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_id: int
    target: str
    action: str
    timestamp: datetime
    reason: str


class AuditEventPage(BaseModel):
    items: list[AuditEventOut]
    page: int
    page_size: int
    total: int


@router.post("/users/{user_id}/deactivate")
def deactivate_user(
    user_id: int,
    payload: ModerationRequest,
    admin: User = Depends(get_current_admin),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    """Deactivate a user and revoke all their existing tokens (F-040)."""

    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="USER_NOT_FOUND",
        )

    if not user.active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="USER_ALREADY_DEACTIVATED",
        )

    user.active = False
    user.token_version += 1

    audit_event = AuditEvent(
        actor_id=admin.id,
        target=f"USER:{user.id}",
        action="USER_DEACTIVATED",
        reason=payload.reason,
    )

    db.add(audit_event)
    db.commit()

    return {
        "message": "User deactivated successfully",
        "user_id": user.id,
        "active": user.active,
    }


@router.post("/listings/{listing_id}/hide")
def hide_listing(
    listing_id: int,
    payload: ModerationRequest,
    admin: User = Depends(get_current_admin),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    """Hide a listing unless it is part of an active exchange (F-040)."""

    listing = db.get(Listing, listing_id)

    if listing is None or listing.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LISTING_NOT_FOUND",
        )

    active_exchange = db.scalar(
        select(Exchange.id).where(
            Exchange.listing_id == listing.id,
            Exchange.state.in_(("ACCEPTED", "ON_LOAN")),
        )
    )

    if active_exchange is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="LISTING_HAS_ACTIVE_EXCHANGE",
        )

    listing.deleted_at = datetime.now(UTC)

    audit_event = AuditEvent(
        actor_id=admin.id,
        target=f"LISTING:{listing.id}",
        action="LISTING_HIDDEN",
        reason=payload.reason,
    )

    db.add(audit_event)
    db.commit()

    return {
        "message": "Listing hidden successfully",
        "listing_id": listing.id,
        "deleted_at": listing.deleted_at,
    }


@router.get("/audit", response_model=AuditEventPage)
def get_audit_log(
    page: int = 1,
    page_size: int = 20,
    admin: User = Depends(get_current_admin),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    """Retrieve administrative audit events (BEP-45)."""

    if page < 1 or page_size < 1 or page_size > 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid pagination parameters",
        )

    total = db.scalar(select(func.count()).select_from(AuditEvent)) or 0

    events = db.scalars(
        select(AuditEvent)
        .order_by(AuditEvent.timestamp.desc(), AuditEvent.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return AuditEventPage(
        items=events,
        page=page,
        page_size=page_size,
        total=total,
    )
