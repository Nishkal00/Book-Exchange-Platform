"""Sprint 1 data model (SAD section 3.6): users, books, listings."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

LISTING_STATUSES = ("AVAILABLE", "UNAVAILABLE", "RESERVED", "ON_LOAN")


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


class Book(Base):
    __tablename__ = "books"
    __table_args__ = (
        CheckConstraint("length(title) BETWEEN 1 AND 200", name="ck_books_title_length"),
        CheckConstraint("length(author) BETWEEN 1 AND 200", name="ck_books_author_length"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    isbn: Mapped[str] = mapped_column(String(13), unique=True)  # normalised: no hyphens
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
