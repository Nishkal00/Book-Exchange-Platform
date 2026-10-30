from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, contains_eager

from app.database import get_db
from app.models import Book, Listing, User
from app.routers.auth import get_current_user

router = APIRouter(prefix="/api/v1/listings", tags=["listings"])

ALLOWED_CONDITIONS = {"NEW", "GOOD", "FAIR", "POOR"}
ALLOWED_UPDATE_STATUSES = {"AVAILABLE", "UNAVAILABLE"}

CONDITION_TO_RANK: dict[str, int] = {
    "POOR": 1,
    "FAIR": 2,
    "GOOD": 3,
    "NEW": 4,
}

RANK_TO_CONDITION: dict[int, str] = {
    1: "POOR",
    2: "FAIR",
    3: "GOOD",
    4: "NEW",
}


class CreateListingRequest(BaseModel):
    """Payload schema for creating a new listing (F-010, SR-004)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=200)
    author: str = Field(min_length=1, max_length=150)
    location: str = Field(min_length=1, max_length=100)
    condition: str
    isbn: str

    @field_validator("condition")
    @classmethod
    def validate_condition(cls, value: str) -> str:
        cleaned = value.strip().upper()
        if cleaned not in ALLOWED_CONDITIONS:
            raise ValueError(f"Condition must be one of: {', '.join(sorted(ALLOWED_CONDITIONS))}")
        return cleaned

    @field_validator("isbn")
    @classmethod
    def validate_isbn(cls, value: str) -> str:
        # F-010: Normalize ISBN by removing hyphens; baseline requires 10 or 13 digits
        cleaned = value.replace("-", "").strip()
        if not (len(cleaned) in (10, 13) and cleaned.isdigit()):
            raise ValueError(
                "ISBN must be 10 or 13 digits after hyphen removal in this course baseline"
            )
        return cleaned


class UpdateListingRequest(BaseModel):
    """Payload schema for partially updating a listing (F-012, SR-005)."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    title: str | None = Field(default=None, min_length=1, max_length=200)
    author: str | None = Field(default=None, min_length=1, max_length=150)
    location: str | None = Field(default=None, min_length=1, max_length=100)
    condition: str | None = None
    isbn: str | None = None
    status: str | None = None

    @field_validator("condition")
    @classmethod
    def validate_condition(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().upper()
        if cleaned not in ALLOWED_CONDITIONS:
            raise ValueError(f"Condition must be one of: {', '.join(sorted(ALLOWED_CONDITIONS))}")
        return cleaned

    @field_validator("isbn")
    @classmethod
    def validate_isbn(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.replace("-", "").strip()
        if not (len(cleaned) in (10, 13) and cleaned.isdigit()):
            raise ValueError(
                "ISBN must be 10 or 13 digits after hyphen removal in this course baseline"
            )
        return cleaned

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().upper()
        if cleaned not in ALLOWED_UPDATE_STATUSES:
            raise ValueError(f"Status must be one of: {', '.join(sorted(ALLOWED_UPDATE_STATUSES))}")
        return cleaned


class ListingOut(BaseModel):
    """Public representation of a listing, omitting secrets and contact details (SAD 4.3)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    author: str
    isbn: str
    condition: str
    location: str
    status: str
    owner_id: int
    created_at: datetime

    @computed_field
    @property
    def ownerId(self) -> int:
        return self.owner_id

    @computed_field
    @property
    def createdAt(self) -> datetime:
        return self.created_at


class PaginatedListingsOut(BaseModel):
    """Paginated collection of listings (SAD 4.3, F-011)."""

    items: list[ListingOut]
    page: int
    size: int
    total: int


def serialize_listing(listing: Listing) -> ListingOut:
    """Helper to convert a Listing model instance with joined Book to ListingOut."""
    return ListingOut(
        id=listing.id,
        title=listing.book.title,
        author=listing.book.author,
        isbn=listing.book.isbn,
        condition=RANK_TO_CONDITION.get(listing.condition_rank, "UNKNOWN"),
        location=listing.location,
        status=listing.status,
        owner_id=listing.owner_id,
        created_at=listing.created_at,
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ListingOut)
def create_listing(
    payload: CreateListingRequest,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> ListingOut:
    """Create a listing for an authenticated owner with status AVAILABLE (F-010).

    Reuses existing book catalog entries by normalized unique ISBN using bound
    SQL/ORM parameters to prevent SQL injection (SR-004).
    """
    normalized_isbn = payload.isbn

    # Safe parameterized query looking up existing book by unique ISBN
    book = db.scalar(select(Book).where(Book.isbn == normalized_isbn))

    if book is None:
        # Create book catalog entry if this ISBN is new
        book = Book(
            isbn=normalized_isbn,
            title=payload.title,
            author=payload.author,
        )
        db.add(book)
        try:
            db.flush()
        except IntegrityError:
            # Handle concurrent insert race condition for the same unique ISBN
            db.rollback()
            book = db.scalar(select(Book).where(Book.isbn == normalized_isbn))
            if book is None:
                raise

    # Create listing for authenticated owner with status AVAILABLE
    condition_rank = CONDITION_TO_RANK[payload.condition]
    listing = Listing(
        owner_id=current_user.id,
        book_id=book.id,
        condition_rank=condition_rank,
        location=payload.location,
        status="AVAILABLE",
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)

    return ListingOut(
        id=listing.id,
        title=book.title,
        author=book.author,
        isbn=book.isbn,
        condition=RANK_TO_CONDITION.get(listing.condition_rank, payload.condition),
        location=listing.location,
        status=listing.status,
        owner_id=listing.owner_id,
        created_at=listing.created_at,
    )


@router.get("/mine", response_model=PaginatedListingsOut)
def get_my_listings(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> PaginatedListingsOut:
    """Return the authenticated caller's non-deleted listings, including unavailable ones (F-011).

    Declared before /{id} to prevent path parameter shadowing (SAD 4.3).
    """
    stmt = (
        select(Listing)
        .join(Listing.book)
        .where(
            Listing.owner_id == current_user.id,
            Listing.deleted_at.is_(None),
        )
    )

    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0

    paginated_stmt = (
        stmt.options(contains_eager(Listing.book))
        .order_by(Listing.created_at.desc(), Listing.id.asc())
        .offset((page - 1) * size)
        .limit(size)
    )
    listings = db.scalars(paginated_stmt).all()

    items = [serialize_listing(item) for item in listings]

    return PaginatedListingsOut(
        items=items,
        page=page,
        size=size,
        total=total,
    )


@router.get("", response_model=PaginatedListingsOut)
def search_listings(
    q: str | None = None,
    isbn: str | None = None,
    location: str | None = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),  # noqa: B008
) -> PaginatedListingsOut:
    """Publicly search AVAILABLE, non-deleted listings (F-011).

    Filters by title/author q, ISBN, and location with pagination.
    """
    stmt = (
        select(Listing)
        .join(Listing.book)
        .where(
            Listing.status == "AVAILABLE",
            Listing.deleted_at.is_(None),
        )
    )

    if q is not None and q.strip():
        q_clean = q.strip()
        stmt = stmt.where(
            or_(
                Book.title.icontains(q_clean, autoescape=True),
                Book.author.icontains(q_clean, autoescape=True),
            )
        )

    if isbn is not None and isbn.strip():
        isbn_raw = isbn.strip()
        isbn_norm = isbn_raw.replace("-", "")
        stmt = stmt.where(
            or_(
                Book.isbn == isbn_norm,
                Book.isbn == isbn_raw,
                Book.isbn.icontains(isbn_norm, autoescape=True),
            )
        )

    if location is not None and location.strip():
        loc_clean = location.strip()
        stmt = stmt.where(Listing.location.icontains(loc_clean, autoescape=True))

    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0

    paginated_stmt = (
        stmt.options(contains_eager(Listing.book))
        .order_by(Listing.created_at.desc(), Listing.id.asc())
        .offset((page - 1) * size)
        .limit(size)
    )
    listings = db.scalars(paginated_stmt).all()

    items = [serialize_listing(item) for item in listings]

    return PaginatedListingsOut(
        items=items,
        page=page,
        size=size,
        total=total,
    )


@router.put("/{listing_id}", response_model=ListingOut)
@router.patch("/{listing_id}", response_model=ListingOut)
def update_listing(
    listing_id: int,
    payload: UpdateListingRequest,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> ListingOut:
    """Allow the owner or admin to partially update a listing (F-012, SR-005).

    - Non-owners receive 403.
    - Missing or soft-deleted IDs receive 404.
    - Reserved or on-loan listings cannot be changed to available or have their book changed (409).
    - Shared book updates reuse or create catalog entries by ISBN rather than modifying other
      listings.
    """
    listing = db.scalar(
        select(Listing)
        .join(Listing.book)
        .options(contains_eager(Listing.book))
        .where(Listing.id == listing_id)
    )

    if listing is None or listing.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listing not found",
        )

    # SR-005: Enforce ownership or explicit admin role server-side
    if listing.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this listing",
        )

    # F-012: Reserved or on-loan listings lifecycle guards
    if listing.status in ("RESERVED", "ON_LOAN"):
        if payload.status == "AVAILABLE":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Reserved or on-loan listings cannot be changed to available",
            )
        # Check if book fields are being changed
        target_isbn = payload.isbn if payload.isbn is not None else listing.book.isbn
        target_title = payload.title if payload.title is not None else listing.book.title
        target_author = payload.author if payload.author is not None else listing.book.author
        if (
            target_isbn != listing.book.isbn
            or target_title != listing.book.title
            or target_author != listing.book.author
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Reserved or on-loan listings cannot have their book changed",
            )

    # F-012 / SAD 4.3: Changing shared book data uses get-or-create ISBN instead of modifying
    # another owner's catalog entry.
    if payload.isbn is not None or payload.title is not None or payload.author is not None:
        target_isbn = payload.isbn if payload.isbn is not None else listing.book.isbn
        target_title = payload.title if payload.title is not None else listing.book.title
        target_author = payload.author if payload.author is not None else listing.book.author

        if (
            target_isbn != listing.book.isbn
            or target_title != listing.book.title
            or target_author != listing.book.author
        ):
            book = db.scalar(select(Book).where(Book.isbn == target_isbn))
            if book is None:
                book = Book(
                    isbn=target_isbn,
                    title=target_title,
                    author=target_author,
                )
                db.add(book)
                try:
                    db.flush()
                except IntegrityError:
                    db.rollback()
                    book = db.scalar(select(Book).where(Book.isbn == target_isbn))
                    if book is None:
                        raise
            listing.book_id = book.id

    if payload.condition is not None:
        listing.condition_rank = CONDITION_TO_RANK[payload.condition]

    if payload.location is not None:
        listing.location = payload.location

    if payload.status is not None:
        listing.status = payload.status

    db.commit()
    db.expire_all()

    updated = db.scalar(
        select(Listing)
        .join(Listing.book)
        .options(contains_eager(Listing.book))
        .where(Listing.id == listing_id)
    )
    return serialize_listing(updated)
