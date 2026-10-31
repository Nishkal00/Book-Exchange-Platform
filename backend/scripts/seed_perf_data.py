"""Seed script for performance and load testing (NF-001 / TC-PERF-01).

Generates synthetic data matching the course test plan specification:
- 20 synthetic users
- ~2,000 books with unique ISBNs and realistic academic titles
- 10,000 listings distributed across users and books
"""

from __future__ import annotations

import argparse
import random
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

# Add backend directory to path if running directly
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import bcrypt  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.database import Base, SessionLocal, make_engine  # noqa: E402
from app.models import Book, Listing, User  # noqa: E402

DISCIPLINES = [
    "Computer Science",
    "Software Engineering",
    "Data Structures",
    "Algorithms",
    "Operating Systems",
    "Computer Networks",
    "Database Systems",
    "Computer Architecture",
    "Artificial Intelligence",
    "Machine Learning",
    "Distributed Systems",
    "Compiler Design",
    "Information Security",
    "Cloud Computing",
    "Discrete Mathematics",
    "Linear Algebra",
    "Probability and Statistics",
    "Digital Logic Design",
    "Web Development",
    "Mobile Computing",
]

SUBTOPICS = [
    "Principles and Practice",
    "Foundations and Applications",
    "A Modern Approach",
    "Concepts and Design",
    "An Algorithmic Introduction",
    "Advanced Theory and Analysis",
    "Practical Guide for Engineers",
    "Core Techniques",
    "Comprehensive Guide",
    "Implementation and Performance",
]

AUTHORS = [
    "Thomas Cormen",
    "Charles Leiserson",
    "Ronald Rivest",
    "Clifford Stein",
    "Andrew Tanenbaum",
    "Abraham Silberschatz",
    "Peter Galvin",
    "Greg Gagne",
    "Robert C. Martin",
    "Martin Fowler",
    "Donald Knuth",
    "Stuart Russell",
    "Peter Norvig",
    "Alfred Aho",
    "Jeffrey Ullman",
    "Erich Gamma",
    "Richard Helm",
    "Ralph Johnson",
    "John Vlissides",
    "David Patterson",
    "John Hennessy",
    "Ian Goodfellow",
    "Yoshua Bengio",
    "Michael Sipser",
    "Jon Kleinberg",
    "Eva Tardos",
    "Ramez Elmasri",
    "Shamkant Navathe",
    "James Kurose",
    "Keith Ross",
]

CAMPUS_LOCATIONS = [
    "Main Library",
    "Engineering Block",
    "Campus Center",
    "Science Library",
    "Hostel 1",
    "Hostel 2",
    "Hostel 3",
    "Hostel 4",
    "North Campus Study Room",
    "South Campus Student Hub",
]


def generate_isbn(index: int) -> str:
    """Generate a valid unique 13-digit normalized ISBN string."""
    return f"978{index:010d}"


def seed_performance_data(
    db: Session,
    num_users: int = 20,
    num_books: int = 2000,
    num_listings: int = 10000,
    clean_first: bool = False,
) -> dict[str, int | float]:
    """Seed synthetic users, books, and listings into the database.

    Returns a summary dictionary with counts and elapsed execution time.
    """
    start_time = time.perf_counter()

    if clean_first:
        db.query(Listing).delete()
        db.query(Book).delete()
        db.query(User).filter(User.email.like("perf_student_%@example.edu")).delete()
        db.commit()

    # 1. Seed synthetic users
    hashed_password = bcrypt.hashpw(b"PerfPassword123!", bcrypt.gensalt()).decode("utf-8")
    existing_users = db.query(User).filter(User.email.like("perf_student_%@example.edu")).all()
    user_ids: list[int] = [u.id for u in existing_users]

    if len(user_ids) < num_users:
        new_users: list[User] = []
        needed = num_users - len(user_ids)
        start_idx = len(user_ids) + 1
        for i in range(start_idx, start_idx + needed):
            loc = CAMPUS_LOCATIONS[i % len(CAMPUS_LOCATIONS)]
            user = User(
                name=f"Performance Student {i}",
                email=f"perf_student_{i}@example.edu",
                password_hash=hashed_password,
                role="student",
                department="Computer Science",
                location=loc,
                active=True,
                token_version=0,
            )
            new_users.append(user)
        db.add_all(new_users)
        db.commit()
        for u in new_users:
            user_ids.append(u.id)

    # 2. Seed books
    existing_books_count = db.query(Book).count()
    book_ids: list[int] = [b.id for b in db.query(Book.id).all()]

    if existing_books_count < num_books:
        needed_books = num_books - existing_books_count
        new_books: list[Book] = []
        start_idx = existing_books_count + 1
        for i in range(start_idx, start_idx + needed_books):
            disc = DISCIPLINES[i % len(DISCIPLINES)]
            sub = SUBTOPICS[(i // len(DISCIPLINES)) % len(SUBTOPICS)]
            vol = f" Vol. {(i % 5) + 1}" if i % 3 == 0 else ""
            title = f"{disc}: {sub}{vol}"
            author = AUTHORS[i % len(AUTHORS)]
            isbn = generate_isbn(i)

            book = Book(
                isbn=isbn,
                title=title[:200],
                author=author[:200],
            )
            new_books.append(book)

        # Batch insert books
        chunk_size = 1000
        for i in range(0, len(new_books), chunk_size):
            chunk = new_books[i : i + chunk_size]
            db.add_all(chunk)
            db.flush()
        db.commit()
        book_ids = [b.id for b in db.query(Book.id).all()]

    # 3. Seed listings
    existing_listings_count = db.query(Listing).count()
    if existing_listings_count < num_listings:
        needed_listings = num_listings - existing_listings_count
        rng = random.Random(42)  # Deterministic seed for reproducible benchmarks
        new_listings: list[Listing] = []

        for _i in range(needed_listings):
            owner_id = rng.choice(user_ids)
            book_id = rng.choice(book_ids)
            condition_rank = rng.randint(1, 4)
            location = rng.choice(CAMPUS_LOCATIONS)

            # Realistic status distribution:
            # ~88% AVAILABLE, ~5% UNAVAILABLE, ~3% RESERVED, ~2% ON_LOAN, ~2% soft-deleted
            roll = rng.random()
            deleted_at = None
            if roll < 0.88:
                status = "AVAILABLE"
            elif roll < 0.93:
                status = "UNAVAILABLE"
            elif roll < 0.96:
                status = "RESERVED"
            elif roll < 0.98:
                status = "ON_LOAN"
            else:
                status = "AVAILABLE"
                deleted_at = datetime.now(UTC)

            listing = Listing(
                owner_id=owner_id,
                book_id=book_id,
                condition_rank=condition_rank,
                location=location,
                status=status,
                deleted_at=deleted_at,
            )
            new_listings.append(listing)

        # Batch insert listings in chunks of 2,000
        chunk_size = 2000
        for i in range(0, len(new_listings), chunk_size):
            chunk = new_listings[i : i + chunk_size]
            db.add_all(chunk)
            db.flush()
        db.commit()

    elapsed = time.perf_counter() - start_time
    total_users = db.query(User).count()
    total_books = db.query(Book).count()
    total_listings = db.query(Listing).count()

    return {
        "users": total_users,
        "books": total_books,
        "listings": total_listings,
        "duration_seconds": round(elapsed, 3),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed performance test dataset (NF-001)")
    parser.add_argument(
        "--users", type=int, default=20, help="Number of synthetic users (default: 20)"
    )
    parser.add_argument("--books", type=int, default=2000, help="Number of books (default: 2000)")
    parser.add_argument(
        "--listings", type=int, default=10000, help="Number of listings (default: 10000)"
    )
    parser.add_argument("--clean", action="store_true", help="Clean synthetic data before seeding")
    parser.add_argument(
        "--db-url",
        type=str,
        default=None,
        help="Optional database URL override (default: configured DATABASE_URL)",
    )
    args = parser.parse_args()

    engine = None
    if args.db_url:
        engine = make_engine(args.db_url)
        Base.metadata.create_all(bind=engine)
        db = Session(engine)
    else:
        db = SessionLocal()

    try:
        print(
            f"Seeding dataset: {args.users} users, ~{args.books} books, {args.listings} listings..."
        )
        result = seed_performance_data(
            db=db,
            num_users=args.users,
            num_books=args.books,
            num_listings=args.listings,
            clean_first=args.clean,
        )
        print("Seeding completed successfully:")
        print(f"  Total users in DB: {result['users']}")
        print(f"  Total books in DB: {result['books']}")
        print(f"  Total listings in DB: {result['listings']}")
        print(f"  Duration: {result['duration_seconds']}s")
    finally:
        db.close()
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    main()
