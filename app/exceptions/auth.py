from app.exceptions.base import UnauthorizedError


class InvalidCredentialsError(UnauthorizedError):
    default_message = "Invalid username or password"
