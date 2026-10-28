import pytest
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models import Book, Listing, User


def make_user(email="a@uni.edu"):
    return User(name="A", email=email, password_hash="x")


def test_user_defaults(db):
    u = make_user()
    db.add(u)
    db.commit()
    assert u.role == "student"
    assert u.active is True
    assert u.token_version == 0


def test_email_must_be_lowercase_and_unique(db):
    db.add(make_user("Upper@uni.edu"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    db.add(make_user("a@uni.edu"))
    db.commit()
    db.add(make_user("a@uni.edu"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_isbn_is_unique(db):
    db.add(Book(isbn="9780131103627", title="C", author="K&R"))
    db.commit()
    db.add(Book(isbn="9780131103627", title="C 2", author="K&R"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_listing_defaults_and_relationships(db):
    u, b = make_user(), Book(isbn="9780131103627", title="C", author="K&R")
    db.add_all([u, b])
    db.commit()
    listing = Listing(owner_id=u.id, book_id=b.id, condition_rank=3)
    db.add(listing)
    db.commit()
    assert listing.status == "AVAILABLE"
    assert listing.deleted_at is None
    assert listing.owner.email == "a@uni.edu"
    assert listing.book.title == "C"


@pytest.mark.parametrize("rank", [0, 5])
def test_condition_rank_range_enforced(db, rank):
    u, b = make_user(), Book(isbn="1234567890", title="T", author="A")
    db.add_all([u, b])
    db.commit()
    db.add(Listing(owner_id=u.id, book_id=b.id, condition_rank=rank))
    with pytest.raises(IntegrityError):
        db.commit()


def test_invalid_status_rejected(db):
    u, b = make_user(), Book(isbn="1234567890", title="T", author="A")
    db.add_all([u, b])
    db.commit()
    db.add(Listing(owner_id=u.id, book_id=b.id, condition_rank=2, status="BROKEN"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_get_db_yields_and_closes_session():
    gen = get_db()
    session = next(gen)
    assert session is not None
    with pytest.raises(StopIteration):
        next(gen)
