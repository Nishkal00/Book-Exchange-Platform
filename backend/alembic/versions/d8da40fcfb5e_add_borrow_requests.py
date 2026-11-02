"""add borrow requests

Revision ID: d8da40fcfb5e
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op

revision = "d8da40fcfb5e"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "borrow_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "student_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("isbn", sa.String(length=13), nullable=True),
        sa.Column("title_query", sa.String(length=200), nullable=True),
        sa.Column("location", sa.String(length=100), nullable=False),
        sa.Column(
            "status",
            sa.String(length=10),
            nullable=False,
            server_default="OPEN",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "(isbn IS NOT NULL AND title_query IS NULL) OR "
            "(isbn IS NULL AND title_query IS NOT NULL)",
            name="ck_borrow_requests_one_criterion",
        ),
        sa.CheckConstraint(
            "status IN ('OPEN', 'FULFILLED', 'CANCELLED')",
            name="ck_borrow_requests_status",
        ),
        sa.CheckConstraint(
            "length(location) BETWEEN 1 AND 100",
            name="ck_borrow_requests_location",
        ),
    )

    op.create_index(
        "ix_borrow_requests_student_id",
        "borrow_requests",
        ["student_id"],
    )
    op.create_index(
        "ix_borrow_requests_status",
        "borrow_requests",
        ["status"],
    )


def downgrade() -> None:
    op.drop_table("borrow_requests")
