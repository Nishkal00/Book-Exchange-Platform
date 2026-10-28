"""users, books, listings, pg_trgm and search indexes

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(10), nullable=False, server_default="student"),
        sa.Column("department", sa.String(100)),
        sa.Column("location", sa.String(100), nullable=False, server_default=""),
        sa.Column("avg_rating", sa.Numeric(3, 2)),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("token_version", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("email = lower(email)", name="ck_users_email_lowercase"),
        sa.CheckConstraint("role IN ('student', 'admin')", name="ck_users_role"),
    )

    op.create_table(
        "books",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("isbn", sa.String(13), nullable=False, unique=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("author", sa.String(200), nullable=False),
        sa.CheckConstraint("length(title) BETWEEN 1 AND 200", name="ck_books_title_length"),
        sa.CheckConstraint("length(author) BETWEEN 1 AND 200", name="ck_books_author_length"),
    )
    op.execute("CREATE INDEX ix_books_title_trgm ON books USING gin (title gin_trgm_ops)")

    op.create_table(
        "listings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("owner_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("book_id", sa.Integer, sa.ForeignKey("books.id"), nullable=False),
        sa.Column("condition_rank", sa.Integer, nullable=False),
        sa.Column("location", sa.String(100), nullable=False, server_default=""),
        sa.Column("status", sa.String(12), nullable=False, server_default="AVAILABLE"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("condition_rank BETWEEN 1 AND 4", name="ck_listings_condition_rank"),
        sa.CheckConstraint(
            "status IN ('AVAILABLE', 'UNAVAILABLE', 'RESERVED', 'ON_LOAN')",
            name="ck_listings_status",
        ),
    )
    op.create_index("ix_listings_owner_id", "listings", ["owner_id"])
    op.create_index("ix_listings_book_id", "listings", ["book_id"])
    op.create_index("ix_listings_status", "listings", ["status"])


def downgrade() -> None:
    op.drop_table("listings")
    op.drop_index("ix_books_title_trgm", table_name="books")
    op.drop_table("books")
    op.drop_table("users")
    # The pg_trgm extension is intentionally left installed; other schemas may use it.
