"""add ratings table

Revision ID: 695e69cb4ad6
Revises: 0004
"""

import sqlalchemy as sa
from alembic import op

revision = "695e69cb4ad6"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ratings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("exchange_id", sa.Integer(), nullable=False),
        sa.Column("rater_id", sa.Integer(), nullable=False),
        sa.Column("ratee_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "rater_id != ratee_id",
            name="ck_ratings_no_self_rating",
        ),
        sa.CheckConstraint(
            "rating BETWEEN 1 AND 5",
            name="ck_ratings_value",
        ),
        sa.ForeignKeyConstraint(
            ["exchange_id"],
            ["exchanges.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["ratee_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["rater_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "exchange_id",
            "rater_id",
            name="uq_ratings_exchange_rater",
        ),
    )

    op.create_index(
        "ix_ratings_ratee",
        "ratings",
        ["ratee_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ratings_ratee", table_name="ratings")
    op.drop_table("ratings")
