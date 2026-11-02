from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Notification, User
from app.routers.auth import get_current_user

router = APIRouter(
    prefix="/api/v1/notifications",
    tags=["notifications"],
)


class NotificationOut(BaseModel):
    """Notification response schema."""

    id: int
    event_type: str
    message: str
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    """Paginated notifications and unread count."""

    items: list[NotificationOut]
    unread_count: int
    total: int


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> NotificationListResponse:
    """List only the authenticated user's notifications."""

    user_filter = Notification.user_id == current_user.id

    notifications = db.scalars(
        select(Notification)
        .where(user_filter)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()

    total = db.scalar(select(func.count()).select_from(Notification).where(user_filter)) or 0

    unread_count = (
        db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(
                user_filter,
                Notification.is_read.is_(False),
            )
        )
        or 0
    )

    return NotificationListResponse(
        items=notifications,
        unread_count=unread_count,
        total=total,
    )


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationOut,
)
def mark_notification_as_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> NotificationOut:
    """Mark one of the authenticated user's notifications as read."""

    notification = db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )

    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    if not notification.is_read:
        notification.is_read = True
        db.commit()
        db.refresh(notification)

    return NotificationOut.model_validate(notification)
