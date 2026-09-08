from app.exceptions.base import UnauthorizedError


class InvalidCredentialsError(UnauthorizedError):
    default_message = "Invalid username or password"


class RefreshTokenInvalidError(UnauthorizedError):
    default_message = "Invalid or expired refresh token"
