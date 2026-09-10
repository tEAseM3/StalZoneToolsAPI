from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.exceptions.user import UserAlreadyExistsError
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.user import UserCreate
from app.services.role import get_role_by_name

DEFAULT_ROLE_NAME = "user"


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, user_data: UserCreate) -> User:
    existing = await get_user_by_username(db, user_data.username)
    if existing is not None:
        raise UserAlreadyExistsError()

    user = User(
        username=user_data.username,
        password_hash=hash_password(user_data.password),
    )
    db.add(user)
    await db.flush()

    default_role = await get_role_by_name(db, DEFAULT_ROLE_NAME)
    if default_role is not None:
        db.add(UserRole(user_id=user.id, role_id=default_role.id))

    await db.commit()
    await db.refresh(user)
    return user
