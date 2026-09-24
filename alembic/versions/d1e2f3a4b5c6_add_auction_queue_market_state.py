"""Add market lifecycle fields to auction queue.

Revision ID: d1e2f3a4b5c6
Revises: c8d1e2f3a4b5
Create Date: 2026-09-24 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d1e2f3a4b5c6"
down_revision: str | Sequence[str] | None = "c8d1e2f3a4b5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "auction_refresh_queue",
        sa.Column("market_state", sa.String(length=16), nullable=False, server_default="probing"),
    )
    op.add_column(
        "auction_refresh_queue",
        sa.Column("empty_probe_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "auction_refresh_queue",
        sa.Column("last_lots_was_empty", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "auction_refresh_queue",
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "auction_refresh_queue",
        sa.Column("retired_reason", sa.String(length=64), nullable=True),
    )
    op.create_check_constraint(
        "check_auction_refresh_queue_market_state",
        "auction_refresh_queue",
        "market_state IN ('probing', 'active', 'retired')",
    )
    op.create_check_constraint(
        "check_auction_refresh_queue_empty_probe_count",
        "auction_refresh_queue",
        "empty_probe_count >= 0",
    )
    op.alter_column("auction_refresh_queue", "market_state", server_default=None)
    op.alter_column("auction_refresh_queue", "empty_probe_count", server_default=None)
    op.alter_column("auction_refresh_queue", "last_lots_was_empty", server_default=None)


def downgrade() -> None:
    op.drop_constraint("check_auction_refresh_queue_empty_probe_count", "auction_refresh_queue")
    op.drop_constraint("check_auction_refresh_queue_market_state", "auction_refresh_queue")
    op.drop_column("auction_refresh_queue", "retired_reason")
    op.drop_column("auction_refresh_queue", "retired_at")
    op.drop_column("auction_refresh_queue", "last_lots_was_empty")
    op.drop_column("auction_refresh_queue", "empty_probe_count")
    op.drop_column("auction_refresh_queue", "market_state")
