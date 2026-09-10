"""Add item , item attribute, sync state tables

Revision ID: 916c9994ae6c
Revises: 6d27c8f4a9b1
Create Date: 2026-09-10 17:17:06.437301

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '916c9994ae6c'
down_revision: Union[str, Sequence[str], None] = '6d27c8f4a9b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
