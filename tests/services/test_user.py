import pytest

from app.exceptions.user import UserAlreadyExistsError
from app.schemas.user import UserCreate
from app.services.user import create_user


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
