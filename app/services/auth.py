from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, verify_password
from app.exceptions.auth import InvalidCredentialsError
from app.schemas.auth import TokenResponse
from app.services.user import get_user_by_username


async def login_user(username: str, password: str, db: AsyncSession) -> TokenResponse:
    user = await get_user_by_username(db, username)

    if user is None:
        raise InvalidCredentialsError()

    if user.deleted_at is not None:
        raise InvalidCredentialsError()

    if not verify_password(password, user.password_hash):
        raise InvalidCredentialsError()

    access_token = create_access_token({"sub": str(user.id)})

    return TokenResponse(access_token=access_token)
