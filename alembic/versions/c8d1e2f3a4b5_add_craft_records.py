"""Add user craft records and trading permissions.

Revision ID: c8d1e2f3a4b5
Revises: b9c1d2e3f4a5
Create Date: 2026-09-24 13:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert

from alembic import op

revision: str = "c8d1e2f3a4b5"
down_revision: str | Sequence[str] | None = "b9c1d2e3f4a5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PERMISSIONS = {
    "trading:read": "Read own craft records and sales",
    "trading:write": "Create own craft records and sales",
}


def upgrade() -> None:
    op.create_table(
        "craft_records",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.String(length=64), nullable=False),
        sa.Column("item_name", sa.String(length=255), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_cost", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("cost_source", sa.String(length=16), nullable=False),
        sa.Column("market_unit_price", sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("length(trim(item_id)) > 0", name="check_craft_record_item_id_length"),
        sa.CheckConstraint("length(trim(item_name)) > 0", name="check_craft_record_item_name_length"),
        sa.CheckConstraint("quantity > 0", name="check_craft_record_quantity"),
        sa.CheckConstraint("unit_cost >= 0", name="check_craft_record_unit_cost"),
        sa.CheckConstraint("market_unit_price >= 0", name="check_craft_record_market_price"),
        sa.CheckConstraint("cost_source IN ('recipe', 'market')", name="check_craft_record_cost_source"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_craft_records_user_item", "craft_records", ["user_id", "item_name"])
    op.create_table(
        "craft_sales",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("record_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("sold_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("quantity > 0", name="check_craft_sale_quantity"),
        sa.CheckConstraint("unit_price >= 0", name="check_craft_sale_unit_price"),
        sa.ForeignKeyConstraint(["record_id"], ["craft_records.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_craft_sales_record", "craft_sales", ["record_id"])
    _seed_permissions()


def downgrade() -> None:
    permissions = sa.table(
        "permissions",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
    )
    role_permissions = sa.table(
        "role_permission",
        sa.column("role_id", sa.Integer),
        sa.column("permission_id", sa.Integer),
    )
    op.execute(
        role_permissions.delete().where(
            role_permissions.c.permission_id.in_(
                sa.select(permissions.c.id).where(permissions.c.name.in_(tuple(PERMISSIONS)))
            )
        )
    )
    op.execute(permissions.delete().where(permissions.c.name.in_(tuple(PERMISSIONS))))
    op.drop_index("idx_craft_sales_record", table_name="craft_sales")
    op.drop_table("craft_sales")
    op.drop_index("idx_craft_records_user_item", table_name="craft_records")
    op.drop_table("craft_records")


def _seed_permissions() -> None:
    permissions = sa.table(
        "permissions",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
    )
    roles = sa.table("roles", sa.column("id", sa.Integer), sa.column("name", sa.String))
    role_permissions = sa.table(
        "role_permission",
        sa.column("role_id", sa.Integer),
        sa.column("permission_id", sa.Integer),
    )
    for name, description in PERMISSIONS.items():
        op.execute(
            insert(permissions)
            .values(name=name, description=description)
            .on_conflict_do_nothing(index_elements=["name"])
        )
    for role_name in ("user", "admin"):
        role_id = sa.select(roles.c.id).where(roles.c.name == role_name).scalar_subquery()
        for permission_name in PERMISSIONS:
            permission_id = (
                sa.select(permissions.c.id)
                .where(permissions.c.name == permission_name)
                .scalar_subquery()
            )
            op.execute(
                insert(role_permissions)
                .values(role_id=role_id, permission_id=permission_id)
                .on_conflict_do_nothing(index_elements=["role_id", "permission_id"])
            )
