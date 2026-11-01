from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from fastapi import Request, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from supabase import ClientOptions, create_client
from supabase_auth import SyncSupportedStorage

from .config import Settings
from .errors import AuthenticationError
from .models import TokenResponse, UserResponse


class MemoryStorage(SyncSupportedStorage):
    def __init__(self, values: dict[str, str] | None = None) -> None:
        self.values = dict(values or {})

    def get_item(self, key: str) -> str | None:
        return self.values.get(key)

    def set_item(self, key: str, value: str) -> None:
        self.values[key] = value

    def remove_item(self, key: str) -> None:
        self.values.pop(key, None)


@dataclass(frozen=True)
class AuthenticatedUser:
    id: UUID
    email: str | None
    display_name: str | None
    avatar_url: str | None

    def response(self) -> UserResponse:
        return UserResponse(**self.__dict__)


class AuthService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.serializer = URLSafeTimedSerializer(
            settings.app_secret_key.get_secret_value(),
            salt="systemlab-supabase-pkce-v1",
        )

    def begin_github_oauth(self) -> tuple[str, str]:
        client, storage = self._client()
        result = client.auth.sign_in_with_oauth(
            {
                "provider": "github",
                "options": {
                    "redirect_to": self.settings.oauth_callback_url,
                    "scopes": "read:user user:email",
                },
            }
        )
        return result.url, self.serializer.dumps(storage.values)

    def finish_github_oauth(self, code: str, signed_flow: str):
        try:
            values = self.serializer.loads(signed_flow, max_age=self.settings.oauth_cookie_max_age)
        except (BadSignature, SignatureExpired) as exc:
            raise AuthenticationError("The OAuth flow expired or is invalid.") from exc
        client, _ = self._client(values)
        try:
            result = client.auth.exchange_code_for_session({"auth_code": code})
        except Exception as exc:
            raise AuthenticationError("GitHub sign-in could not be completed.") from exc
        if result.session is None:
            raise AuthenticationError("GitHub sign-in did not create a session.")
        return result.session

    def refresh(self, refresh_token: str) -> tuple[TokenResponse, str]:
        client, _ = self._client()
        try:
            result = client.auth.refresh_session(refresh_token)
        except Exception as exc:
            raise AuthenticationError("The refresh session is invalid or expired.") from exc
        if result.session is None:
            raise AuthenticationError("The refresh session is invalid or expired.")
        user = self._map_user(result.session.user)
        return TokenResponse(
            access_token=result.session.access_token,
            expires_in=result.session.expires_in,
            user=user.response(),
        ), result.session.refresh_token

    def authenticate(self, access_token: str) -> AuthenticatedUser:
        client, _ = self._client()
        try:
            result = client.auth.get_user(access_token)
        except Exception as exc:
            raise AuthenticationError() from exc
        return self._map_user(result.user)

    def logout(self, access_token: str | None, refresh_token: str | None) -> None:
        if not access_token or not refresh_token:
            return
        client, _ = self._client()
        try:
            client.auth.set_session(access_token, refresh_token)
            client.auth.sign_out()
        except Exception:
            # Cookie deletion is the guaranteed local logout path.
            return

    def set_oauth_cookie(self, response: Response, value: str) -> None:
        response.set_cookie(
            self.settings.oauth_cookie_name,
            value,
            max_age=self.settings.oauth_cookie_max_age,
            httponly=True,
            secure=self.settings.cookie_secure,
            samesite="lax",
            path="/api/v1/auth",
        )

    def set_refresh_cookie(self, response: Response, value: str) -> None:
        response.set_cookie(
            self.settings.refresh_cookie_name,
            value,
            max_age=self.settings.refresh_cookie_max_age,
            httponly=True,
            secure=self.settings.cookie_secure,
            samesite="lax",
            path="/api/v1/auth",
        )

    def clear_oauth_cookie(self, response: Response) -> None:
        response.delete_cookie(self.settings.oauth_cookie_name, path="/api/v1/auth")

    def clear_refresh_cookie(self, response: Response) -> None:
        response.delete_cookie(self.settings.refresh_cookie_name, path="/api/v1/auth")

    def _client(self, values: dict[str, str] | None = None):
        storage = MemoryStorage(values)
        options = ClientOptions(
            flow_type="pkce",
            storage=storage,
            persist_session=True,
            auto_refresh_token=False,
        )
        client = create_client(
            str(self.settings.supabase_url).rstrip("/"),
            self.settings.supabase_publishable_key.get_secret_value(),
            options,
        )
        return client, storage

    @staticmethod
    def _map_user(user: Any) -> AuthenticatedUser:
        metadata = getattr(user, "user_metadata", None) or {}
        return AuthenticatedUser(
            id=UUID(str(user.id)),
            email=getattr(user, "email", None),
            display_name=metadata.get("full_name") or metadata.get("name") or metadata.get("user_name"),
            avatar_url=metadata.get("avatar_url"),
        )


def bearer_token(request: Request, *, required: bool = True) -> str | None:
    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        if required:
            raise AuthenticationError()
        return None
    return token
