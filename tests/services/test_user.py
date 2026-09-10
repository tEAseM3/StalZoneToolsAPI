import pytest
from sqlalchemy import select

from app.exceptions.user import UserAlreadyExistsError
from app.models.role import Role
from app.models.user_role import UserRole
from app.schemas.user import UserCreate
from app.services.user import create_user, get_user_by_id, get_user_by_username


async def _create_user(db_session, username="user", password="password123"):
    return await create_user(db_session, UserCreate(username=username, password=password))


# create_user


async def test_create_user_success(db_session):
    user = await _create_user(db_session)

    assert user.id is not None
    assert user.password_hash != "password123"


async def test_create_user_duplicate_username_raises(db_session):
    await _create_user(db_session)

    with pytest.raises(UserAlreadyExistsError):
        await _create_user(db_session)


async def test_create_user_assigns_default_role_when_it_exists(db_session):
    db_session.add(Role(name="user"))
    await db_session.commit()

    user = await _create_user(db_session)

    result = await db_session.execute(select(UserRole).where(UserRole.user_id == user.id))
    user_role = result.scalar_one()
    assert user_role.role_id is not None


async def test_create_user_succeeds_when_default_role_is_missing(db_session):
    user = await _create_user(db_session)

    result = await db_session.execute(select(UserRole).where(UserRole.user_id == user.id))
    assert result.scalar_one_or_none() is None


# get_user_by_username


async def test_get_user_by_username_returns_existing_user(db_session):
    created_user = await _create_user(db_session)

    user = await get_user_by_username(db_session, created_user.username)

    assert user is not None
    assert user.id == created_user.id


async def test_get_user_by_username_returns_none_when_user_is_missing(db_session):
    user = await get_user_by_username(db_session, "unknown")

    assert user is None


# get_user_by_id


async def test_get_user_by_id_returns_existing_user(db_session):
    created_user = await _create_user(db_session)

    user = await get_user_by_id(db_session, created_user.id)

    assert user is not None
    assert user.username == created_user.username


async def test_get_user_by_id_returns_none_when_user_is_missing(db_session):
    user = await get_user_by_id(db_session, 999)

    assert user is None
