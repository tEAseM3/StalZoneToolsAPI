from app.exceptions.base import ConflictError


class UserAlreadyExistsError(ConflictError):
    default_message = "Username already taken"
