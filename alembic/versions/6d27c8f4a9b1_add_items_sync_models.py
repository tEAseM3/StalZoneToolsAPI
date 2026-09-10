"""Add item synchronization models

Revision ID: 6d27c8f4a9b1
Revises: 40049f66a7e6
Create Date: 2026-09-10 18:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "6d27c8f4a9b1"
down_revision: str | Sequence[str] | None = "40049f66a7e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "items",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("source_path", sa.String(length=512), nullable=False),
        sa.Column("category", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("color", sa.String(length=55), nullable=True),
        sa.Column("status_state", sa.String(length=55), nullable=True),
        sa.Column("raw", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_sha", sa.String(length=64), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("length(trim(category)) > 0", name="check_item_category_length"),
        sa.CheckConstraint("length(trim(id)) > 0", name="check_item_id_length"),
        sa.CheckConstraint("length(trim(name)) > 0", name="check_item_name_length"),
        sa.CheckConstraint("length(trim(source_path)) > 0", name="check_item_source_path_length"),
        sa.CheckConstraint("length(trim(source_sha)) > 0", name="check_item_source_sha_length"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_path"),
    )
    op.create_index("idx_items_category", "items", ["category"], unique=False)
    op.create_index("idx_items_raw_gin", "items", ["raw"], unique=False, postgresql_using="gin")

    op.create_table(
        "item_attributes",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("item_id", sa.String(length=64), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("value_text", sa.Text(), nullable=True),
        sa.Column("value_numeric", sa.Numeric(), nullable=True),
        sa.Column("unit_label", sa.String(length=255), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "value_text IS NOT NULL OR value_numeric IS NOT NULL",
            name="check_item_attribute_has_value",
        ),
        sa.CheckConstraint("length(trim(key)) > 0", name="check_item_attribute_key_length"),
        sa.CheckConstraint("sort_order >= 0", name="check_item_attribute_sort_order"),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_item_attributes_item", "item_attributes", ["item_id"], unique=False)
    op.create_index("idx_item_attributes_key", "item_attributes", ["key"], unique=False)

    op.create_table(
        "sync_state",
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("key"),
    )


def downgrade() -> None:
    op.drop_table("sync_state")
    op.drop_index("idx_item_attributes_key", table_name="item_attributes")
    op.drop_index("idx_item_attributes_item", table_name="item_attributes")
    op.drop_table("item_attributes")
    op.drop_index("idx_items_raw_gin", table_name="items")
    op.drop_index("idx_items_category", table_name="items")
    op.drop_table("items")
