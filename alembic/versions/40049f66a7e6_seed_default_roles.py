"""Seed default roles

Revision ID: 40049f66a7e6
Revises: cff6f6e23123
Create Date: 2026-09-10 14:09:53.959791

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '40049f66a7e6'
down_revision: Union[str, Sequence[str], None] = 'cff6f6e23123'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    roles_table = sa.table(
        "roles",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
    )

    op.bulk_insert(
        roles_table,
        [
            {"name": "user", "description": "Default role"},
            {"name": "admin", "description": "Full access"},
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM roles WHERE name IN ('user', 'admin')")
