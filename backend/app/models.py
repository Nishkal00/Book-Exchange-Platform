"""Data models for users, books, listings, borrow requests, matches, and exchanges."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

LISTING_STATUSES = ("AVAILABLE", "UNAVAILABLE", "RESERVED", "ON_LOAN")
BORROW_REQUEST_STATUSES = ("OPEN", "MATCHED", "FULFILLED", "CANCELLED")
MATCH_STATUSES = ("PROPOSED", "ACCEPTED", "DECLINED", "EXPIRED")
EXCHANGE_STATES = ("ACCEPTED", "ON_LOAN", "RETURNED", "CANCELLED")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("email = lower(email)", name="ck_users_email_lowercase"),
        CheckConstraint("role IN ('student', 'admin')", name="ck_users_role"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(10), default="student", server_default="student")
    department: Mapped[str | None] = mapped_column(String(100))
    location: Mapped[str] = mapped_column(String(100), default="", server_default="")
    avg_rating: Mapped[float | None] = mapped_column(Numeric(3, 2))
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    token_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    listings: Mapped[list["Listing"]] = relationship(back_populates="owner")
    borrow_requests: Mapped[list["BorrowRequest"]] = relationship(back_populates="borrower")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="user")


class Book(Base):
    __tablename__ = "books"
    __table_args__ = (
        CheckConstraint("length(title) BETWEEN 1 AND 200", name="ck_books_title_length"),
        CheckConstraint("length(author) BETWEEN 1 AND 200", name="ck_books_author_length"),
        Index("ix_books_title", "title"),
        Index("ix_books_author", "author"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    isbn: Mapped[str] = mapped_column(String(13), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    author: Mapped[str] = mapped_column(String(200))

    listings: Mapped[list["Listing"]] = relationship(back_populates="book")


class Listing(Base):
    __tablename__ = "listings"
    __table_args__ = (
        CheckConstraint("condition_rank BETWEEN 1 AND 4", name="ck_listings_condition_rank"),
        CheckConstraint(
            "status IN ('AVAILABLE', 'UNAVAILABLE', 'RESERVED', 'ON_LOAN')",
            name="ck_listings_status",
        ),
        Index(
            "ix_listings_status_deleted_created",
            "status",
            "deleted_at",
            "created_at",
        ),
        Index("ix_listings_location", "location"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), index=True)
    condition_rank: Mapped[int] = mapped_column(Integer)
    location: Mapped[str] = mapped_column(String(100), default="", server_default="")
    status: Mapped[str] = mapped_column(
        String(12), default="AVAILABLE", server_default="AVAILABLE", index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    owner: Mapped[User] = relationship(back_populates="listings")
    book: Mapped[Book] = relationship(back_populates="listings")
    matches: Mapped[list["Match"]] = relationship("Match", back_populates="listing")
    exchanges: Mapped[list["Exchange"]] = relationship("Exchange", back_populates="listing")


class BorrowRequest(Base):
    __tablename__ = "borrow_requests"
    __table_args__ = (
        CheckConstraint(
            "status IN ('OPEN', 'MATCHED', 'FULFILLED', 'CANCELLED')",
            name="ck_borrow_requests_status",
        ),
        CheckConstraint(
            "isbn IS NOT NULL OR (query IS NOT NULL AND length(trim(query)) > 0)",
            name="ck_borrow_requests_criteria",
        ),
        Index("ix_borrow_requests_borrower_status", "borrower_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    borrower_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    isbn: Mapped[str | None] = mapped_column(String(13), index=True)
    query: Mapped[str | None] = mapped_column(String(200))
    location: Mapped[str] = mapped_column(String(100), default="", server_default="")
    status: Mapped[str] = mapped_column(
        String(20), default="OPEN", server_default="OPEN", index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    borrower: Mapped[User] = relationship("User", back_populates="borrow_requests")
    matches: Mapped[list["Match"]] = relationship("Match", back_populates="request")
    exchanges: Mapped[list["Exchange"]] = relationship("Exchange", back_populates="request")


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PROPOSED', 'ACCEPTED', 'DECLINED', 'EXPIRED')",
            name="ck_matches_status",
        ),
        Index("ix_matches_request_listing", "request_id", "listing_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("borrow_requests.id"), index=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"), index=True)
    score: Mapped[float] = mapped_column(Numeric(5, 2))
    relevance: Mapped[float] = mapped_column(Numeric(5, 2), default=1.0, server_default="1.0")
    borrower_accepted: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    lender_accepted: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    status: Mapped[str] = mapped_column(
        String(20), default="PROPOSED", server_default="PROPOSED", index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    request: Mapped[BorrowRequest] = relationship("BorrowRequest", back_populates="matches")
    listing: Mapped[Listing] = relationship("Listing", back_populates="matches")
    exchange: Mapped["Exchange | None"] = relationship(
        "Exchange", back_populates="match", uselist=False
    )


class Exchange(Base):
    __tablename__ = "exchanges"
    __table_args__ = (
        CheckConstraint(
            "state IN ('ACCEPTED', 'ON_LOAN', 'RETURNED', 'CANCELLED')",
            name="ck_exchanges_state",
        ),
        Index(
            "uq_active_exchange_listing",
            "listing_id",
            unique=True,
            sqlite_where=text("state IN ('ACCEPTED', 'ON_LOAN')"),
            postgresql_where=text("state IN ('ACCEPTED', 'ON_LOAN')"),
        ),
        Index(
            "uq_active_exchange_request",
            "request_id",
            unique=True,
            sqlite_where=text("state IN ('ACCEPTED', 'ON_LOAN')"),
            postgresql_where=text("state IN ('ACCEPTED', 'ON_LOAN')"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), unique=True, index=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("borrow_requests.id"), index=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"), index=True)
    state: Mapped[str] = mapped_column(
        String(20), default="ACCEPTED", server_default="ACCEPTED", index=True
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    handover_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    borrower_return_confirmed: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    lender_return_confirmed: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    match: Mapped[Match] = relationship("Match", back_populates="exchange")
    request: Mapped[BorrowRequest] = relationship("BorrowRequest", back_populates="exchanges")
    listing: Mapped[Listing] = relationship("Listing", back_populates="exchanges")


class Notification(Base):
    __tablename__ = "notifications"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "event_key",
            name="uq_notifications_user_event",
        ),
        CheckConstraint(
            "event_type IN ('MATCH_FOUND', 'PARTNER_DECISION', 'EXCHANGE_UPDATED')",
            name="ck_notifications_event_type",
        ),
        Index(
            "ix_notifications_user_created",
            "user_id",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    event_key: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    event_type: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    message: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="notifications")
