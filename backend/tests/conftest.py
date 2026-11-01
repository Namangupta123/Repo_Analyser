from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from systemlab_backend.auth import AuthenticatedUser
from systemlab_backend.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        supabase_url="https://example.supabase.co",
        supabase_publishable_key="sb_publishable_test",
        database_url="postgresql://postgres:password@localhost:5432/postgres",
        app_secret_key="a" * 32,
        frontend_url="http://localhost:5173",
        backend_url="http://localhost:8000",
        cors_origins=["http://localhost:5173"],
        cookie_secure=False,
    )


class FakeAuth:
    def __init__(self, settings: Settings, user_id: UUID | None = None) -> None:
        self.settings = settings
        self.user = AuthenticatedUser(user_id or uuid4(), "user@example.com", "User", None)
        self.logout_args = None

    def authenticate(self, token: str) -> AuthenticatedUser:
        if token != "valid-token":
            raise AssertionError("unexpected test token")
        return self.user

    def begin_github_oauth(self):
        return "https://github.com/login/oauth/authorize", "signed-flow"

    def finish_github_oauth(self, code: str, signed_flow: str):
        assert code == "code"
        assert signed_flow == "signed-flow"
        return SimpleNamespace(refresh_token="refresh-token")

    def refresh(self, refresh_token: str):
        from systemlab_backend.models import TokenResponse

        assert refresh_token == "refresh-token"
        return TokenResponse(access_token="access-token", expires_in=3600, user=self.user.response()), "rotated-token"

    def logout(self, access_token, refresh_token):
        self.logout_args = (access_token, refresh_token)

    def set_oauth_cookie(self, response, value):
        response.set_cookie(self.settings.oauth_cookie_name, value, httponly=True, samesite="lax")

    def set_refresh_cookie(self, response, value):
        response.set_cookie(self.settings.refresh_cookie_name, value, httponly=True, samesite="lax")

    def clear_oauth_cookie(self, response):
        response.delete_cookie(self.settings.oauth_cookie_name)

    def clear_refresh_cookie(self, response):
        response.delete_cookie(self.settings.refresh_cookie_name)


class FakeRepository:
    def __init__(self, user_id: UUID) -> None:
        self.user_id = user_id
        self.analysis_id = uuid4()
        self.status = "QUEUED"
        self.artifacts = {"graph": {"nodes": []}, "report": {"status": "COMPLETED"}, "errors": {"errors": []}}

    def row(self):
        now = datetime.now(timezone.utc)
        return {
            "id": self.analysis_id,
            "user_id": self.user_id,
            "repository_url": "https://github.com/owner/repository",
            "status": self.status,
            "commit_sha": None,
            "analyzer_version": None,
            "schema_version": None,
            "metrics": {},
            "attempt_count": 0,
            "failure_message": None,
            "created_at": now,
            "started_at": None,
            "completed_at": None,
            "updated_at": now,
        }

    def ready(self):
        return True

    def create_and_enqueue(self, user_id, repository_url):
        assert user_id == self.user_id
        row = self.row()
        row["repository_url"] = repository_url
        return row

    def list_for_user(self, user_id, limit, offset):
        return [self.row()] if user_id == self.user_id else []

    def get_for_user(self, user_id, analysis_id):
        from systemlab_backend.errors import NotFoundError

        if user_id != self.user_id or analysis_id != self.analysis_id:
            raise NotFoundError()
        return self.row()

    def get_artifact_for_user(self, user_id, analysis_id, field):
        from systemlab_backend.errors import BackendError

        self.get_for_user(user_id, analysis_id)
        if self.status in {"QUEUED", "RUNNING"}:
            raise BackendError(409, "ANALYSIS_NOT_READY", "not ready")
        return self.artifacts[field]

    def delete_for_user(self, user_id, analysis_id):
        from systemlab_backend.errors import BackendError

        self.get_for_user(user_id, analysis_id)
        if self.status in {"QUEUED", "RUNNING"}:
            raise BackendError(409, "ANALYSIS_ACTIVE", "active")


@pytest.fixture
def fake_services(settings):
    auth = FakeAuth(settings)
    return auth, FakeRepository(auth.user.id)
