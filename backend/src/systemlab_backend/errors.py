from __future__ import annotations

from typing import Any


class BackendError(Exception):
    def __init__(self, status_code: int, code: str, message: str, *, headers: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.headers = headers or {}

    def detail(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message}


class NotFoundError(BackendError):
    def __init__(self, message: str = "Analysis was not found.") -> None:
        super().__init__(404, "ANALYSIS_NOT_FOUND", message)


class AuthenticationError(BackendError):
    def __init__(self, message: str = "Authentication is required") -> None:
        super().__init__(401, "AUTHENTICATION_REQUIRED", message, headers={"WWW-Authenticate": "Bearer"})

