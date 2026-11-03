"""exchange_events history table (F-025)

Revision ID: 0004
Revises: 3ff23e857997
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "3ff23e857997"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "exchange_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("exchange_id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=30), nullable=False),
        sa.Column("from_state", sa.String(length=20), nullable=True),
        sa.Column("to_state", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["exchange_id"], ["exchanges.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_exchange_events_exchange_created",
        "exchange_events",
        ["exchange_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_exchange_events_exchange_created", table_name="exchange_events")
    op.drop_table("exchange_events")
