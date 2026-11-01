from __future__ import annotations

import pytest
from pydantic import ValidationError

from systemlab_backend.config import Settings
from systemlab_backend.models import AnalysisCreateRequest


def test_settings_require_server_secrets(settings: Settings) -> None:
    assert settings.database_url.get_secret_value().startswith("postgresql://")
    assert settings.oauth_callback_url == "http://localhost:8000/api/v1/auth/callback"
    assert "a" * 32 not in repr(settings)


def test_settings_reject_short_app_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(
            supabase_url="https://example.supabase.co",
            supabase_publishable_key="key",
            database_url="postgresql://localhost/db",
            app_secret_key="short",
        )


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/owner/repo",
        "https://gitlab.com/owner/repo",
        "https://github.com/owner/repo?token=secret",
        "https://github.com/owner/repo/tree/main",
    ],
)
def test_create_request_rejects_non_exact_public_github_urls(url: str) -> None:
    with pytest.raises(ValidationError):
        AnalysisCreateRequest(repository_url=url)


def test_create_request_normalizes_git_suffix() -> None:
    request = AnalysisCreateRequest(repository_url="https://github.com/owner/repo.git")
    assert request.repository_url == "https://github.com/owner/repo"
