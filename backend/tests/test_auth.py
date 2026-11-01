from __future__ import annotations

import pytest
from fastapi import Response

from systemlab_backend.auth import AuthService, MemoryStorage
from systemlab_backend.errors import AuthenticationError


def test_refresh_cookie_is_secure_httponly_and_scoped(settings) -> None:
    secure_settings = settings.model_copy(update={"cookie_secure": True})
    response = Response()
    AuthService(secure_settings).set_refresh_cookie(response, "never-returned-in-json")
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    assert "SameSite=lax" in cookie
    assert "Path=/api/v1/auth" in cookie


def test_tampered_pkce_cookie_is_rejected_before_exchange(settings) -> None:
    service = AuthService(settings)
    signed = service.serializer.dumps({"code-verifier": "value"})
    with pytest.raises(AuthenticationError):
        service.finish_github_oauth("code", f"{signed}tampered")


def test_memory_storage_does_not_share_request_state() -> None:
    first = MemoryStorage()
    second = MemoryStorage()
    first.set_item("verifier", "secret")
    assert second.get_item("verifier") is None
