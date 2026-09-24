from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User
from app.models.user_role import UserRole
from app.services.role import get_role_by_name
from app.services.user import get_user_by_username


async def ensure_test_admin(db: AsyncSession, username: str, password: str) -> User:
    user = await get_user_by_username(db, username)
    if user is None:
        user = User(username=username, password_hash=hash_password(password))
        db.add(user)
        await db.flush()
    else:
        user.password_hash = hash_password(password)

    admin_role = await get_role_by_name(db, "admin")
    if admin_role is None:
        raise RuntimeError("The 'admin' role must be seeded before the test user")
    if await db.get(UserRole, {"user_id": user.id, "role_id": admin_role.id}) is None:
        db.add(UserRole(user_id=user.id, role_id=admin_role.id))

    await db.commit()
    await db.refresh(user)
    return user
