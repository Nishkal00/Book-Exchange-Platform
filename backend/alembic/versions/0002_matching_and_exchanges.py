"""borrow_requests, matches, exchanges, constraints and partial unique indexes (SAD 3.6)

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "borrow_requests",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("borrower_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("isbn", sa.String(13)),
        sa.Column("query", sa.String(200)),
        sa.Column("location", sa.String(100), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="OPEN"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "status IN ('OPEN', 'MATCHED', 'FULFILLED', 'CANCELLED')",
            name="ck_borrow_requests_status",
        ),
        sa.CheckConstraint(
            "isbn IS NOT NULL OR (query IS NOT NULL AND length(trim(query)) > 0)",
            name="ck_borrow_requests_criteria",
        ),
    )
    op.create_index("ix_borrow_requests_borrower_id", "borrow_requests", ["borrower_id"])
    op.create_index("ix_borrow_requests_status", "borrow_requests", ["status"])

    op.create_table(
        "matches",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("request_id", sa.Integer, sa.ForeignKey("borrow_requests.id"), nullable=False),
        sa.Column("listing_id", sa.Integer, sa.ForeignKey("listings.id"), nullable=False),
        sa.Column("score", sa.Numeric(5, 2), nullable=False),
        sa.Column("relevance", sa.Numeric(5, 2), nullable=False, server_default="1.0"),
        sa.Column("borrower_accepted", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("lender_accepted", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(20), nullable=False, server_default="PROPOSED"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('PROPOSED', 'ACCEPTED', 'DECLINED', 'EXPIRED')",
            name="ck_matches_status",
        ),
    )
    op.create_index("ix_matches_request_id", "matches", ["request_id"])
    op.create_index("ix_matches_listing_id", "matches", ["listing_id"])
    op.create_index("ix_matches_status", "matches", ["status"])
    op.create_index("ix_matches_request_listing", "matches", ["request_id", "listing_id"])

    op.create_table(
        "exchanges",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("match_id", sa.Integer, sa.ForeignKey("matches.id"), nullable=False, unique=True),
        sa.Column("request_id", sa.Integer, sa.ForeignKey("borrow_requests.id"), nullable=False),
        sa.Column("listing_id", sa.Integer, sa.ForeignKey("listings.id"), nullable=False),
        sa.Column("state", sa.String(20), nullable=False, server_default="ACCEPTED"),
        sa.Column("due_at", sa.DateTime(timezone=True)),
        sa.Column("handover_confirmed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "borrower_return_confirmed",
            sa.Boolean,
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "lender_return_confirmed",
            sa.Boolean,
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("returned_at", sa.DateTime(timezone=True)),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "state IN ('ACCEPTED', 'ON_LOAN', 'RETURNED', 'CANCELLED')",
            name="ck_exchanges_state",
        ),
    )
    op.create_index("ix_exchanges_request_id", "exchanges", ["request_id"])
    op.create_index("ix_exchanges_listing_id", "exchanges", ["listing_id"])

    # Partial unique indexes: exactly one active exchange per listing and per request
    op.create_index(
        "uq_active_exchange_listing",
        "exchanges",
        ["listing_id"],
        unique=True,
        postgresql_where=sa.text("state IN ('ACCEPTED', 'ON_LOAN')"),
        sqlite_where=sa.text("state IN ('ACCEPTED', 'ON_LOAN')"),
    )
    op.create_index(
        "uq_active_exchange_request",
        "exchanges",
        ["request_id"],
        unique=True,
        postgresql_where=sa.text("state IN ('ACCEPTED', 'ON_LOAN')"),
        sqlite_where=sa.text("state IN ('ACCEPTED', 'ON_LOAN')"),
    )


def downgrade() -> None:
    op.drop_index("uq_active_exchange_request", table_name="exchanges")
    op.drop_index("uq_active_exchange_listing", table_name="exchanges")
    op.drop_table("exchanges")
    op.drop_table("matches")
    op.drop_table("borrow_requests")
