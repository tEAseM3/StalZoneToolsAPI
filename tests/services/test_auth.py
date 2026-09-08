from datetime import UTC, datetime

import pytest

from app.exceptions.auth import InvalidCredentialsError, RefreshTokenInvalidError
from app.schemas.user import UserCreate
from app.services.auth import login_user, logout_user, refresh_access_token
from app.services.user import create_user


async def _create_user(db_session, username="user", password="password123"):
    return await create_user(db_session, UserCreate(username=username, password=password))


# login_user


async def test_login_user_success(db_session):
    await _create_user(db_session)

    tokens = await login_user("user", "password123", db_session)

    assert tokens.access_token
    assert tokens.refresh_token
    assert tokens.token_type == "bearer"


async def test_login_user_invalid_password_raises(db_session):
    await _create_user(db_session)

    with pytest.raises(InvalidCredentialsError):
        await login_user("user", "wrong-password", db_session)


async def test_login_user_unknown_username_raises(db_session):
    with pytest.raises(InvalidCredentialsError):
        await login_user("unknown", "password123", db_session)


async def test_soft_deleted_user_cannot_login(db_session):
    user = await _create_user(db_session)
    user.deleted_at = datetime.now(UTC)
    await db_session.commit()

    with pytest.raises(InvalidCredentialsError):
        await login_user("user", "password123", db_session)


# refresh_access_token


async def test_refresh_access_token_rotates_refresh_token(db_session):
    await _create_user(db_session)
    tokens = await login_user("user", "password123", db_session)

    refreshed = await refresh_access_token(tokens.refresh_token, db_session)

    assert refreshed.refresh_token != tokens.refresh_token

    with pytest.raises(RefreshTokenInvalidError):
        await refresh_access_token(tokens.refresh_token, db_session)


async def test_invalid_refresh_token_raises(db_session):
    with pytest.raises(RefreshTokenInvalidError):
        await refresh_access_token("invalid-token", db_session)


# logout_user


async def test_logout_user_revokes_refresh_token(db_session):
    await _create_user(db_session)
    tokens = await login_user("user", "password123", db_session)

    await logout_user(tokens.refresh_token, db_session)

    with pytest.raises(RefreshTokenInvalidError):
        await refresh_access_token(tokens.refresh_token, db_session)
