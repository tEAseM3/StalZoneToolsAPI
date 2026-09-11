"""Add hideout recipe models

Revision ID: 71d4ab3c8f2e
Revises: 916c9994ae6c
Create Date: 2026-09-11 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "71d4ab3c8f2e"
down_revision: str | Sequence[str] | None = "916c9994ae6c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "hideout_perks",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("raw", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.CheckConstraint("length(trim(id)) > 0", name="check_hideout_perk_id_length"),
        sa.CheckConstraint("length(trim(name)) > 0", name="check_hideout_perk_name_length"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "hideout_recipes",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("source_index", sa.Integer(), nullable=False),
        sa.Column("bench", sa.String(length=64), nullable=False),
        sa.Column("category_key", sa.String(length=255), nullable=False),
        sa.Column("category_name", sa.String(length=255), nullable=False),
        sa.Column("subcategory_key", sa.String(length=255), nullable=True),
        sa.Column("subcategory_name", sa.String(length=255), nullable=True),
        sa.Column("energy", sa.Numeric(), nullable=False),
        sa.Column("required_perks", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("required_features", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("raw", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_sha", sa.String(length=64), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("source_index >= 0", name="check_hideout_recipe_source_index"),
        sa.CheckConstraint("length(trim(bench)) > 0", name="check_hideout_recipe_bench_length"),
        sa.CheckConstraint("length(trim(category_key)) > 0", name="check_hideout_recipe_category_key_length"),
        sa.CheckConstraint("length(trim(category_name)) > 0", name="check_hideout_recipe_category_name_length"),
        sa.CheckConstraint("energy >= 0", name="check_hideout_recipe_energy"),
        sa.CheckConstraint("length(trim(source_sha)) > 0", name="check_hideout_recipe_source_sha_length"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_index"),
    )
    op.create_index("idx_hideout_recipes_bench", "hideout_recipes", ["bench"], unique=False)
    op.create_index("idx_hideout_recipes_category_key", "hideout_recipes", ["category_key"], unique=False)
    op.create_index("idx_hideout_recipes_subcategory_key", "hideout_recipes", ["subcategory_key"], unique=False)
    op.create_index("idx_hideout_recipes_raw_gin", "hideout_recipes", ["raw"], unique=False, postgresql_using="gin")
    op.create_table(
        "hideout_recipe_items",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("recipe_id", sa.BigInteger(), nullable=False),
        sa.Column("component_type", sa.String(length=16), nullable=False),
        sa.Column("item_id", sa.String(length=64), nullable=False),
        sa.Column("amount", sa.Numeric(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.CheckConstraint("component_type IN ('ingredient', 'result')", name="check_hideout_recipe_item_component_type"),
        sa.CheckConstraint("length(trim(item_id)) > 0", name="check_hideout_recipe_item_id_length"),
        sa.CheckConstraint("amount > 0", name="check_hideout_recipe_item_amount"),
        sa.CheckConstraint("sort_order >= 0", name="check_hideout_recipe_item_sort_order"),
        sa.ForeignKeyConstraint(["recipe_id"], ["hideout_recipes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_hideout_recipe_items_recipe", "hideout_recipe_items", ["recipe_id"], unique=False)
    op.create_index("idx_hideout_recipe_items_item", "hideout_recipe_items", ["item_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_hideout_recipe_items_item", table_name="hideout_recipe_items")
    op.drop_index("idx_hideout_recipe_items_recipe", table_name="hideout_recipe_items")
    op.drop_table("hideout_recipe_items")
    op.drop_index("idx_hideout_recipes_raw_gin", table_name="hideout_recipes")
    op.drop_index("idx_hideout_recipes_subcategory_key", table_name="hideout_recipes")
    op.drop_index("idx_hideout_recipes_category_key", table_name="hideout_recipes")
    op.drop_index("idx_hideout_recipes_bench", table_name="hideout_recipes")
    op.drop_table("hideout_recipes")
    op.drop_table("hideout_perks")
