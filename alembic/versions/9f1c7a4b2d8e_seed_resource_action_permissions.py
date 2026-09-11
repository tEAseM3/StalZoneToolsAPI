"""Seed resource action permissions

Revision ID: 9f1c7a4b2d8e
Revises: 71d4ab3c8f2e
Create Date: 2026-09-11 13:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert

from alembic import op

revision: str = "9f1c7a4b2d8e"
down_revision: str | Sequence[str] | None = "71d4ab3c8f2e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PERMISSIONS = {
    "profile:read": "Read own profile",
    "auction:read": "Read auction prices and history",
    "items:read": "Read item catalogue",
    "hideout:read": "Read hideout recipes and perks",
    "system:read": "Read system synchronization status",
}

USER_PERMISSIONS = ("profile:read", "auction:read", "items:read", "hideout:read")
ADMIN_PERMISSIONS = tuple(PERMISSIONS)
LEGACY_PERMISSIONS = ("profile", "auction", "items", "hideout", "admin")


def upgrade() -> None:
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

    op.execute(
        role_permissions.delete().where(
            role_permissions.c.permission_id.in_(
                sa.select(permissions.c.id).where(permissions.c.name.in_(LEGACY_PERMISSIONS))
            )
        )
    )
    op.execute(permissions.delete().where(permissions.c.name.in_(LEGACY_PERMISSIONS)))

    _assign_permissions(role_permissions, roles, permissions, "user", USER_PERMISSIONS)
    _assign_permissions(role_permissions, roles, permissions, "admin", ADMIN_PERMISSIONS)


def downgrade() -> None:
    permissions = sa.table(
        "permissions",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
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


def _assign_permissions(role_permissions, roles, permissions, role_name: str, names: tuple[str, ...]):
    role_id = sa.select(roles.c.id).where(roles.c.name == role_name).scalar_subquery()
    for permission_name in names:
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
