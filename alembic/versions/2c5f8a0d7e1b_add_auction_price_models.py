"""Add auction price models

Revision ID: 2c5f8a0d7e1b
Revises: 9f1c7a4b2d8e
Create Date: 2026-09-11 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "2c5f8a0d7e1b"
down_revision: str | Sequence[str] | None = "9f1c7a4b2d8e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "auction_trades",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("region", sa.String(length=3), nullable=False),
        sa.Column("item_id", sa.String(length=64), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("lot_price", sa.BigInteger(), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("sold_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("region IN ('RU', 'EU', 'NA', 'SEA', 'NEA')", name="check_auction_trade_region"),
        sa.CheckConstraint("length(trim(item_id)) > 0", name="check_auction_trade_item_id_length"),
        sa.CheckConstraint("amount > 0", name="check_auction_trade_amount"),
        sa.CheckConstraint("lot_price >= 0", name="check_auction_trade_lot_price"),
        sa.CheckConstraint("unit_price >= 0", name="check_auction_trade_unit_price"),
        sa.CheckConstraint("length(trim(source_fingerprint)) > 0", name="check_auction_trade_fingerprint_length"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_fingerprint"),
    )
    op.create_index("idx_auction_trades_region_item_sold_at", "auction_trades", ["region", "item_id", "sold_at"], unique=False)
    op.create_table(
        "auction_current_prices",
        sa.Column("region", sa.String(length=3), nullable=False),
        sa.Column("item_id", sa.String(length=64), nullable=False),
        sa.Column("best_buyout_unit_price", sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column("best_bid_unit_price", sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column("lots_total", sa.Integer(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("region IN ('RU', 'EU', 'NA', 'SEA', 'NEA')", name="check_auction_current_price_region"),
        sa.CheckConstraint("length(trim(item_id)) > 0", name="check_auction_current_price_item_id_length"),
        sa.CheckConstraint("best_buyout_unit_price >= 0", name="check_auction_buyout_unit_price"),
        sa.CheckConstraint("best_bid_unit_price >= 0", name="check_auction_bid_unit_price"),
        sa.CheckConstraint("lots_total >= 0", name="check_auction_lots_total"),
        sa.PrimaryKeyConstraint("region", "item_id"),
    )
    op.create_index("idx_auction_current_prices_region_observed", "auction_current_prices", ["region", "observed_at"], unique=False)
    op.create_table(
        "auction_price_candles",
        sa.Column("region", sa.String(length=3), nullable=False),
        sa.Column("item_id", sa.String(length=64), nullable=False),
        sa.Column("interval", sa.String(length=8), nullable=False),
        sa.Column("bucket_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("median_unit_price", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("vwap_unit_price", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("min_unit_price", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("max_unit_price", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("percentile_10_unit_price", sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column("percentile_90_unit_price", sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column("trade_count", sa.Integer(), nullable=False),
        sa.Column("volume", sa.Integer(), nullable=False),
        sa.Column("turnover", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("region IN ('RU', 'EU', 'NA', 'SEA', 'NEA')", name="check_auction_candle_region"),
        sa.CheckConstraint("length(trim(item_id)) > 0", name="check_auction_candle_item_id_length"),
        sa.CheckConstraint("interval IN ('day', 'week')", name="check_auction_candle_interval"),
        sa.CheckConstraint("median_unit_price >= 0", name="check_auction_candle_median"),
        sa.CheckConstraint("vwap_unit_price >= 0", name="check_auction_candle_vwap"),
        sa.CheckConstraint("min_unit_price >= 0", name="check_auction_candle_min"),
        sa.CheckConstraint("max_unit_price >= 0", name="check_auction_candle_max"),
        sa.CheckConstraint("trade_count >= 0", name="check_auction_candle_trade_count"),
        sa.CheckConstraint("volume >= 0", name="check_auction_candle_volume"),
        sa.CheckConstraint("turnover >= 0", name="check_auction_candle_turnover"),
        sa.PrimaryKeyConstraint("region", "item_id", "interval", "bucket_start"),
    )
    op.create_index("idx_auction_price_candles_region_item_interval", "auction_price_candles", ["region", "item_id", "interval"], unique=False)
    op.create_table(
        "auction_refresh_queue",
        sa.Column("region", sa.String(length=3), nullable=False),
        sa.Column("item_id", sa.String(length=64), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("next_lots_refresh_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_history_refresh_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_lots_refresh_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_history_refresh_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("region IN ('RU', 'EU', 'NA', 'SEA', 'NEA')", name="check_auction_refresh_queue_region"),
        sa.CheckConstraint("length(trim(item_id)) > 0", name="check_auction_refresh_queue_item_id_length"),
        sa.CheckConstraint("priority >= 0", name="check_auction_refresh_queue_priority"),
        sa.PrimaryKeyConstraint("region", "item_id"),
    )
    op.create_table(
        "craft_profit_snapshots",
        sa.Column("recipe_id", sa.BigInteger(), nullable=False),
        sa.Column("region", sa.String(length=3), nullable=False),
        sa.Column("result_value", sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column("ingredients_cost", sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column("energy_required", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("energy_item_amount", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("energy_cost", sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column("total_cost", sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column("profit", sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column("margin_percent", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("has_complete_prices", sa.Boolean(), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("region IN ('RU', 'EU', 'NA', 'SEA', 'NEA')", name="check_craft_profit_snapshot_region"),
        sa.CheckConstraint("energy_required >= 0", name="check_craft_profit_energy_required"),
        sa.CheckConstraint("energy_item_amount >= 0", name="check_craft_profit_energy_item_amount"),
        sa.ForeignKeyConstraint(["recipe_id"], ["hideout_recipes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("recipe_id", "region"),
    )
    op.create_index("idx_craft_profit_snapshots_region_profit", "craft_profit_snapshots", ["region", "profit"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_craft_profit_snapshots_region_profit", table_name="craft_profit_snapshots")
    op.drop_table("craft_profit_snapshots")
    op.drop_table("auction_refresh_queue")
    op.drop_index("idx_auction_price_candles_region_item_interval", table_name="auction_price_candles")
    op.drop_table("auction_price_candles")
    op.drop_index("idx_auction_current_prices_region_observed", table_name="auction_current_prices")
    op.drop_table("auction_current_prices")
    op.drop_index("idx_auction_trades_region_item_sold_at", table_name="auction_trades")
    op.drop_table("auction_trades")
