
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import BorrowRequest, User
from app.routers.auth import get_current_user

router = APIRouter(prefix="/api/v1/requests", tags=["requests"])


class CreateBorrowRequest(BaseModel):
    """Payload for creating a borrow request (F-020)."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    isbn: str | None = Field(default=None, min_length=10, max_length=17)
    title_query: str | None = Field(default=None, min_length=1, max_length=200)
    location: str = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_criterion(self):
        if bool(self.isbn) == bool(self.title_query):
            raise ValueError("Provide exactly one of isbn or title_query")

        if self.isbn is not None:
            normalized = self.isbn.replace("-", "").replace(" ", "")
            if len(normalized) not in (10, 13) or not normalized.isdigit():
                raise ValueError("ISBN must contain 10 or 13 digits")
            self.isbn = normalized

        if self.title_query is not None and not self.title_query.strip():
            raise ValueError("Title query cannot be empty")

        return self


class BorrowRequestOut(BaseModel):
    """Public representation of a borrow request."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    isbn: str | None
    title_query: str | None
    location: str
    status: str
    created_at: datetime


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=BorrowRequestOut,
)
def create_borrow_request(
    payload: CreateBorrowRequest,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> BorrowRequestOut:
    """Create an OPEN borrow request for the authenticated student."""

    criteria = [
        BorrowRequest.student_id == current_user.id,
        BorrowRequest.status == "OPEN",
    ]

    if payload.isbn is not None:
        criteria.append(BorrowRequest.isbn == payload.isbn)
    else:
        criteria.append(BorrowRequest.title_query == payload.title_query)

    existing = db.scalar(select(BorrowRequest).where(*criteria))

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An active borrow request with this criterion already exists",
        )

    borrow_request = BorrowRequest(
        student_id=current_user.id,
        isbn=payload.isbn,
        title_query=payload.title_query,
        location=payload.location,
        status="OPEN",
    )

    db.add(borrow_request)
    db.commit()
    db.refresh(borrow_request)

    return borrow_request
