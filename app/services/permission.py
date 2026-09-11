from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.permission import Permission
from app.models.role_permission import RolePermission
from app.models.user_role import UserRole


async def get_user_permission_names(db: AsyncSession, user_id: int) -> set[str]:
    result = await db.scalars(
        select(Permission.name)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .where(UserRole.user_id == user_id)
    )
    return set(result)


async def user_has_permissions(
    db: AsyncSession, user_id: int, required_permissions: set[str]
) -> bool:
    return required_permissions.issubset(await get_user_permission_names(db, user_id))
