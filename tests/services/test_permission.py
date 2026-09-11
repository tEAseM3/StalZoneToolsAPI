from sqlalchemy import select

from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user import User
from app.models.user_role import UserRole
from app.services.permission import get_user_permission_names, user_has_permissions


async def test_get_user_permission_names_returns_permissions_from_all_roles(db_session):
    user = User(username="reader", password_hash="hash")
    item_role = Role(name="item-reader")
    hideout_role = Role(name="hideout-reader")
    item_permission = Permission(name="items:read")
    hideout_permission = Permission(name="hideout:read")
    db_session.add_all([user, item_role, hideout_role, item_permission, hideout_permission])
    await db_session.flush()
    db_session.add_all(
        [
            UserRole(user_id=user.id, role_id=item_role.id),
            UserRole(user_id=user.id, role_id=hideout_role.id),
            RolePermission(role_id=item_role.id, permission_id=item_permission.id),
            RolePermission(role_id=hideout_role.id, permission_id=hideout_permission.id),
        ]
    )
    await db_session.commit()

    assert await get_user_permission_names(db_session, user.id) == {"items:read", "hideout:read"}
    assert await user_has_permissions(db_session, user.id, {"items:read"}) is True
    assert await user_has_permissions(db_session, user.id, {"items:read", "auction:read"}) is False


async def test_permission_name_is_queryable_after_relationship_assignment(db_session):
    permission = Permission(name="system:read")
    db_session.add(permission)
    await db_session.commit()

    assert await db_session.scalar(select(Permission.name)) == "system:read"
