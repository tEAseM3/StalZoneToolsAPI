class NotFoundError(Exception):
    default_message = "Resource not found"

    def __init__(self, message: str | None = None):
        super().__init__(message or self.default_message)


class ConflictError(Exception):
    default_message = "Conflict"

    def __init__(self, message: str | None = None):
        super().__init__(message or self.default_message)


class ForbiddenError(Exception):
    default_message = "Forbidden"

    def __init__(self, message: str | None = None):
        super().__init__(message or self.default_message)


class UnauthorizedError(Exception):
    default_message = "Unauthorized"

    def __init__(self, message: str | None = None):
        super().__init__(message or self.default_message)
